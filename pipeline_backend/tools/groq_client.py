from __future__ import annotations

from typing import Any

import httpx

from pipeline_backend.config import GROQ_API_KEY, GROQ_MODEL


class GroqChatClient:
    def __init__(self, *, api_key: str = GROQ_API_KEY, model: str = GROQ_MODEL, timeout: float = 120.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, *, system_prompt: str, user_prompt: str, max_tokens: int = 1200) -> str:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        return str(choices[0].get("message", {}).get("content", ""))

