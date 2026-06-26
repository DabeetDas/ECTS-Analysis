from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
DEFAULT_TRANSFORMERS_MODEL = (
    os.getenv("TRANSFORMERS_MODEL_PATH")
    or os.getenv("TRANSFORMERS_MODEL_ID")
    or "Qwen/Qwen3-8B"
)

torch = None
AutoModelForCausalLM = None
AutoTokenizer = None
BitsAndBytesConfig = None


class LLMClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return a JSON string for the supplied prompt."""


@dataclass
class OpenRouterClient:
    """OpenRouter API adapter using the OpenAI-compatible SDK.

    The dependency is imported lazily so the rest of the package can be tested
    before you manually add `openai` to the environment.
    """

    model: str = DEFAULT_OPENROUTER_MODEL
    api_key: str | None = None
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 1.0
    stream: bool = False
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: float = 120.0
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    _client: Any = field(default=None, init=False, repr=False)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        client = self._get_client()
        attempts = max(1, self.max_retries)
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                completion = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    top_p=self.top_p,
                    stream=self.stream,
                    stop=None,
                )

                text = self._collect_stream(completion) if self.stream else self._collect_message(completion)
                if not text:
                    raise RuntimeError("OpenRouter returned an empty response")
                return normalize_json_response(text)
            except Exception as exc:
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(self.retry_backoff_seconds * (2**attempt))

        raise RuntimeError(f"OpenRouter request failed after {attempts} attempt(s)") from last_error

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ImportError(
                    "OpenRouterClient requires the `openai` package. "
                    "Add it manually, then rerun the pipeline."
                ) from exc

            api_key = self.api_key or os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                raise RuntimeError("Set OPENROUTER_API_KEY before using OpenRouterClient.")
            kwargs = {"api_key": api_key, "base_url": self.base_url, "timeout": self.timeout_seconds}
            self._client = OpenAI(**kwargs)
        return self._client

    def _collect_stream(self, completion: Any) -> str:
        parts: list[str] = []
        for chunk in completion:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None)
            if content:
                parts.append(content)
        return "".join(parts)

    def _collect_message(self, completion: Any) -> str:
        choices = getattr(completion, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        return getattr(message, "content", None) or ""


@dataclass
class OllamaClient:
    """Local Ollama API adapter using the built-in HTTP client."""

    model: str
    base_url: str = "http://localhost:11434"
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 1.0
    timeout_seconds: float = 120.0
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        attempts = max(1, self.max_retries)
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                payload = self._post_chat(
                    {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "top_p": self.top_p,
                            "num_predict": self.max_tokens,
                        },
                    }
                )
                message = payload.get("message", {})
                text = message.get("content") if isinstance(message, dict) else None
                if not isinstance(text, str) or not text:
                    raise RuntimeError("Ollama returned an empty response")
                return normalize_json_response(text)
            except Exception as exc:
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(self.retry_backoff_seconds * (2**attempt))

        raise RuntimeError(f"Ollama request failed after {attempts} attempt(s)") from last_error

    def _post_chat(self, payload: dict[str, object]) -> dict[str, object]:
        url = f"{self.base_url.rstrip('/')}/api/chat"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not reach Ollama at {self.base_url}") from exc

        if not isinstance(response_payload, dict):
            raise RuntimeError("Ollama returned a non-object response")
        return response_payload


@dataclass
class QwenTransformersClient:
    """Local Qwen adapter that loads a Transformers checkpoint from local files."""

    model: str = DEFAULT_TRANSFORMERS_MODEL
    max_input_tokens: int = 32768
    max_tokens: int = 4096
    generation_max_time_seconds: float | None = None
    device_map: str = "auto"
    torch_dtype: str = "auto"
    trust_remote_code: bool = False
    local_files_only: bool = True
    load_in_4bit: bool = False
    load_in_8bit: bool = False
    enable_thinking: bool = False
    _model_source: str | None = field(default=None, init=False, repr=False)
    _tokenizer: Any = field(default=None, init=False, repr=False)
    _model: Any = field(default=None, init=False, repr=False)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self._load()
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"{user_prompt}\n\nReturn only valid JSON. Do not include markdown.",
            },
        ]
        inputs = self._tokenize_messages(messages)
        input_device = model_input_device(self._model)
        inputs = {key: value.to(input_device) for key, value in inputs.items()}
        prompt_tokens = inputs["input_ids"].shape[-1]

        with torch.inference_mode():
            generate_kwargs = {
                **inputs,
                "max_length": prompt_tokens + max(1, self.max_tokens),
                "do_sample": False,
                "pad_token_id": self._tokenizer.pad_token_id,
                "eos_token_id": self._tokenizer.eos_token_id,
            }
            if self.generation_max_time_seconds is not None and self.generation_max_time_seconds > 0:
                generate_kwargs["max_time"] = self.generation_max_time_seconds
            generated = self._model.generate(**generate_kwargs)

        generated_tokens = generated[0][prompt_tokens:]
        raw = self._tokenizer.decode(generated_tokens, skip_special_tokens=False)
        return normalize_json_response(strip_qwen_response(raw))

    def _load(self) -> None:
        if self._model is not None:
            return

        ensure_transformers_imports()
        self._model_source = resolve_model_source(self.model, self.local_files_only)
        tokenizer_kwargs = {
            "trust_remote_code": self.trust_remote_code,
            "local_files_only": self.local_files_only,
        }
        model_kwargs: dict[str, object] = {
            "device_map": self.device_map,
            "trust_remote_code": self.trust_remote_code,
            "local_files_only": self.local_files_only,
        }
        parsed_dtype = parse_torch_dtype(self.torch_dtype)
        if parsed_dtype is not None:
            model_kwargs["torch_dtype"] = parsed_dtype
        quantization_config = build_quantization_config(self.load_in_4bit, self.load_in_8bit)
        if quantization_config is not None:
            model_kwargs["quantization_config"] = quantization_config

        self._tokenizer = AutoTokenizer.from_pretrained(self._model_source, **tokenizer_kwargs)
        if self._tokenizer.pad_token_id is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token
        self._model = AutoModelForCausalLM.from_pretrained(self._model_source, **model_kwargs)
        self._model.eval()

    def _tokenize_messages(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        if getattr(self._tokenizer, "chat_template", None):
            try:
                tokenized = apply_chat_template(
                    self._tokenizer,
                    messages,
                    self.max_input_tokens,
                    self.enable_thinking,
                )
                return normalize_tokenizer_output(tokenized)
            except Exception:
                pass

        prompt_text = build_plain_prompt(messages)
        return normalize_tokenizer_output(
            self._tokenizer(
                prompt_text,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_input_tokens,
            )
        )


def ensure_transformers_imports() -> None:
    global torch, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    if torch is not None:
        return
    try:
        import torch as torch_module
        from transformers import (
            AutoModelForCausalLM as auto_model_for_causal_lm,
            AutoTokenizer as auto_tokenizer,
            BitsAndBytesConfig as bits_and_bytes_config,
        )
    except (ImportError, ModuleNotFoundError) as exc:
        missing = exc.name or "required package"
        raise ModuleNotFoundError(
            f"Missing dependency '{missing}'. Install torch and transformers first."
        ) from exc

    torch = torch_module
    AutoModelForCausalLM = auto_model_for_causal_lm
    AutoTokenizer = auto_tokenizer
    BitsAndBytesConfig = bits_and_bytes_config


def is_gguf_file(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"GGUF"
    except OSError:
        return False


def resolve_model_source(model_ref: str, local_files_only: bool) -> str:
    path = Path(model_ref).expanduser()
    if path.exists():
        resolved_path = path.resolve()
        if resolved_path.is_file():
            if is_gguf_file(resolved_path):
                raise ValueError(
                    f"{resolved_path} is a GGUF file. Pass a Transformers checkpoint "
                    "directory containing config.json and tokenizer/model files."
                )
            raise ValueError(f"{resolved_path} is a file. Pass the model directory.")
        return str(resolved_path)

    if local_files_only:
        raise FileNotFoundError(
            f"Model path not found: {path}. Pass your local Qwen checkpoint directory "
            "with --model, or set TRANSFORMERS_MODEL_PATH."
        )

    return model_ref


def parse_torch_dtype(dtype_name: str | None):
    if not dtype_name or dtype_name == "auto":
        return None
    ensure_transformers_imports()
    dtype_map = {
        "bfloat16": torch.bfloat16,
        "bf16": torch.bfloat16,
        "float16": torch.float16,
        "fp16": torch.float16,
        "float32": torch.float32,
        "fp32": torch.float32,
    }
    if dtype_name not in dtype_map:
        raise ValueError(f"Unsupported torch dtype: {dtype_name}")
    return dtype_map[dtype_name]


def build_quantization_config(load_in_4bit: bool, load_in_8bit: bool):
    if load_in_4bit and load_in_8bit:
        raise ValueError("Choose only one of TRANSFORMERS_LOAD_IN_4BIT or TRANSFORMERS_LOAD_IN_8BIT.")
    if not load_in_4bit and not load_in_8bit:
        return None

    ensure_transformers_imports()
    if load_in_4bit:
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
    return BitsAndBytesConfig(load_in_8bit=True)


def model_input_device(model):
    try:
        return model.get_input_embeddings().weight.device
    except Exception:
        return next(model.parameters()).device


def apply_chat_template(
    tokenizer: Any,
    messages: list[dict[str, str]],
    max_input_tokens: int,
    enable_thinking: bool,
):
    template_kwargs = {
        "add_generation_prompt": True,
        "return_tensors": "pt",
        "truncation": True,
        "max_length": max_input_tokens,
    }
    if enable_thinking:
        return tokenizer.apply_chat_template(messages, **template_kwargs)

    try:
        return tokenizer.apply_chat_template(messages, enable_thinking=False, **template_kwargs)
    except Exception:
        return tokenizer.apply_chat_template(messages, **template_kwargs)


def build_plain_prompt(messages: list[dict[str, str]]) -> str:
    parts = []
    for message in messages:
        role = message["role"].upper()
        parts.append(f"{role}:\n{message['content']}")
    parts.append("ASSISTANT:\n")
    return "\n\n".join(parts)


def normalize_tokenizer_output(tokenized) -> dict[str, Any]:
    if hasattr(tokenized, "keys"):
        return {key: tokenized[key] for key in tokenized.keys()}
    return {"input_ids": tokenized}


def strip_qwen_response(raw: str) -> str:
    content = raw.strip()
    if "</think>" in content:
        content = content.split("</think>", 1)[1].strip()
    else:
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    if "```json" in content:
        content = content.split("```json", 1)[1]
        content = content.split("```", 1)[0]
    elif "```" in content:
        content = content.split("```", 1)[1]
        content = content.split("```", 1)[0]

    json_start_positions = [
        position for position in (content.find("{"), content.find("[")) if position != -1
    ]
    if json_start_positions:
        content = content[min(json_start_positions) :]

    content = re.sub(r"<\|[^|]*\|>", "", content).strip()
    return content


def normalize_json_response(text: str) -> str:
    """Return a JSON string, tolerating fenced JSON from the model."""

    stripped = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1).strip()

    try:
        json.loads(stripped)
        return stripped
    except json.JSONDecodeError:
        pass

    first_array = stripped.find("[")
    first_object = stripped.find("{")
    starts = [index for index in (first_array, first_object) if index >= 0]
    if not starts:
        raise ValueError("LLM response did not contain JSON")
    start = min(starts)

    for end in range(len(stripped), start, -1):
        candidate = stripped[start:end].strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue

    raise ValueError("LLM response contained malformed JSON")
