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
        client = self._get_client()
        result = client.generate(
            inputs=user_prompt,
            max_new_tokens=self.max_tokens,
            do_sample=False,
            top_p=self.top_p,
            temperature=self.temperature,
        )
        text = result.generated_text
        if not text:
            raise RuntimeError("Qwen Transformers returned an empty response")
        return normalize_json_response(text)

    def _get_client(self) -> Any:
        global torch, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        if self._model is None:
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            except ImportError as exc:
                raise ImportError(
                    "QwenTransformersClient requires `torch` and `transformers`. "
                    "Install them manually if you want to use this model."
                ) from exc

            self._model_source = self.model
            tokenizer = AutoTokenizer.from_pretrained(
                self.model,
                trust_remote_code=self.trust_remote_code,
                local_files_only=self.local_files_only,
            )
            config = BitsAndBytesConfig(
                load_in_4bit=self.load_in_4bit,
                llm_int8_threshold=6.0,
                llm_int8_enable_fp32_cpu_offload=False,
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model,
                device_map=self.device_map,
                torch_dtype=getattr(torch, self.torch_dtype, torch.float32),
                trust_remote_code=self.trust_remote_code,
                local_files_only=self.local_files_only,
                quantization_config=config if self.load_in_4bit or self.load_in_8bit else None,
            )
        return self._model


def normalize_json_response(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text
