import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from ects_analysis.demo import build_llm_client
from ects_analysis.llm import (
    OllamaClient,
    OpenRouterClient,
    QwenTransformersClient,
    resolve_model_source,
    strip_qwen_response,
)


class FakeCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("test timeout")
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='[{"topic_name": "Deposits"}]')
                )
            ]
        )


class FakeOpenRouterSdkClient:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


class OpenRouterClientTests(unittest.TestCase):
    def test_complete_retries_after_transient_timeout(self) -> None:
        sdk_client = FakeOpenRouterSdkClient()
        client = OpenRouterClient(max_retries=2, retry_backoff_seconds=0)
        client._client = sdk_client

        response = client.complete("system", "user")

        self.assertEqual(response, '[{"topic_name": "Deposits"}]')
        self.assertEqual(sdk_client.completions.calls, 2)

    def test_streaming_is_disabled_by_default_for_json_calls(self) -> None:
        client = OpenRouterClient()

        self.assertFalse(client.stream)


class OllamaClientTests(unittest.TestCase):
    def test_complete_sends_model_to_local_ollama_api(self) -> None:
        calls: list[dict[str, object]] = []
        client = OllamaClient(model="/models/local-model", max_retries=1)

        def fake_post_chat(payload: dict[str, object]) -> dict[str, object]:
            calls.append(payload)
            return {"message": {"content": '[{"topic_name": "Deposits"}]'}}

        client._post_chat = fake_post_chat  # type: ignore[method-assign]

        response = client.complete("system", "user")

        self.assertEqual(response, '[{"topic_name": "Deposits"}]')
        self.assertEqual(calls[0]["model"], "/models/local-model")

    def test_complete_retries_after_transient_ollama_error(self) -> None:
        calls = 0
        client = OllamaClient(model="local", max_retries=2, retry_backoff_seconds=0)

        def fake_post_chat(payload: dict[str, object]) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise TimeoutError("test timeout")
            return {"message": {"content": '[{"topic_name": "Deposits"}]'}}

        client._post_chat = fake_post_chat  # type: ignore[method-assign]

        response = client.complete("system", "user")

        self.assertEqual(response, '[{"topic_name": "Deposits"}]')
        self.assertEqual(calls, 2)


class QwenTransformersClientTests(unittest.TestCase):
    def test_build_llm_client_supports_qwen_provider(self) -> None:
        client = build_llm_client("qwen", "/models/qwen")

        self.assertIsInstance(client, QwenTransformersClient)
        self.assertEqual(client.model, "/models/qwen")

    def test_resolve_model_source_accepts_local_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            model_dir = Path(temp_dir)

            self.assertEqual(resolve_model_source(str(model_dir), local_files_only=True), str(model_dir))

    def test_resolve_model_source_rejects_gguf_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            model_file = Path(temp_dir) / "model.gguf"
            model_file.write_bytes(b"GGUF")

            with self.assertRaisesRegex(ValueError, "GGUF file"):
                resolve_model_source(str(model_file), local_files_only=True)

    def test_strip_qwen_response_removes_thinking_and_fences(self) -> None:
        raw = '<think>reasoning</think>\n```json\n[{"topic_name": "Deposits"}]\n```<|end|>'

        self.assertEqual(strip_qwen_response(raw), '[{"topic_name": "Deposits"}]')


if __name__ == "__main__":
    unittest.main()
