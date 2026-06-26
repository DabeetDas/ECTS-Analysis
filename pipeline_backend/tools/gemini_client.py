from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from pipeline_backend.config import GEMINI_API_KEY, GEMINI_MODEL

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRIES = 5
BASE_DELAY  = 2  # seconds (doubled each attempt: 2, 4, 8, 16, 32)

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
FILES_UPLOAD_ENDPOINT = (
    "https://generativelanguage.googleapis.com/upload/v1beta/files"
)
FILES_DELETE_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/files/{file_id}"
)

# Inline base64 is fine for small files; anything larger goes through the
# Files API to avoid hammering token quotas (50-page PDFs ≈ 10–20 MB).
INLINE_SIZE_LIMIT_BYTES = 512 * 1024  # 512 KB


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str = GEMINI_API_KEY,
        model: str = GEMINI_MODEL,
        timeout: float = 120.0,
        delete_uploaded_files: bool = True,
    ) -> None:
        self.api_key               = api_key
        self.model                 = model
        self.timeout               = timeout
        self.delete_uploaded_files = delete_uploaded_files

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def generate_json_from_file(self, path: Path, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        mime_type  = _guess_mime_type(path)
        file_uri   = None
        file_part  = self._build_file_part(path, mime_type)

        # file_part is None when the file was uploaded via the Files API;
        # in that case _build_file_part stores the URI for us.
        if isinstance(file_part, str):
            # URI returned from Files API
            file_uri  = file_part
            file_part = {"file_data": {"mime_type": mime_type, "file_uri": file_uri}}

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}, file_part]}],
            "generationConfig": {
                "temperature":        0,
                "response_mime_type": "application/json",
            },
        }

        try:
            response = self._post_with_retry(
                GEMINI_ENDPOINT.format(model=self.model), payload
            )
            return _parse_json_text(_extract_gemini_text(response))
        finally:
            if file_uri and self.delete_uploaded_files:
                self._delete_file(file_uri)

    # ------------------------------------------------------------------
    # File handling
    # ------------------------------------------------------------------

    def _build_file_part(self, path: Path, mime_type: str) -> dict[str, Any] | str:
        """Return an inline part dict, or a Files-API URI string for large files."""
        if mime_type.startswith("text/"):
            return {"text": path.read_text(encoding="utf-8", errors="ignore")}

        if path.stat().st_size <= INLINE_SIZE_LIMIT_BYTES:
            import base64
            return {
                "inline_data": {
                    "mime_type": mime_type,
                    "data":      base64.b64encode(path.read_bytes()).decode("ascii"),
                }
            }

        # Large binary file — upload once, reference by URI
        return self._upload_file(path, mime_type)

    def _upload_file(self, path: Path, mime_type: str) -> str:
        """Upload to the Gemini Files API and return the file URI."""
        boundary = "GeminiBoundary"
        metadata = json.dumps({"file": {"display_name": path.name}}).encode()
        body = (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
            .encode()
            + metadata
            + f"\r\n--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n".encode()
            + path.read_bytes()
            + f"\r\n--{boundary}--".encode()
        )

        with httpx.Client(timeout=120) as client:
            response = client.post(
                FILES_UPLOAD_ENDPOINT,
                params={"key": self.api_key, "uploadType": "multipart"},
                content=body,
                headers={"Content-Type": f"multipart/related; boundary={boundary}"},
            )
            response.raise_for_status()

        file_uri = response.json()["file"]["uri"]
        print(f"[Gemini] Uploaded '{path.name}' → {file_uri}")
        return file_uri

    def _delete_file(self, file_uri: str) -> None:
        """Delete a previously uploaded file from the Files API."""
        file_id = file_uri.rstrip("/").split("/")[-1]
        try:
            with httpx.Client(timeout=30) as client:
                client.delete(
                    FILES_DELETE_ENDPOINT.format(file_id=file_id),
                    params={"key": self.api_key},
                )
            print(f"[Gemini] Deleted uploaded file '{file_id}'")
        except Exception as exc:  # noqa: BLE001
            # Non-fatal — log and move on
            print(f"[Gemini] Warning: could not delete file '{file_id}': {exc}")

    # ------------------------------------------------------------------
    # HTTP with retry
    # ------------------------------------------------------------------

    def _post_with_retry(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST *payload* to *url*, retrying on 429 with exponential backoff."""
        for attempt in range(MAX_RETRIES):
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url, params={"key": self.api_key}, json=payload
                )

            if response.status_code != 429:
                response.raise_for_status()
                return response.json()

            if attempt == MAX_RETRIES - 1:
                response.raise_for_status()  # raise the 429 after final attempt

            delay = int(
                response.headers.get("Retry-After", BASE_DELAY * (2 ** attempt))
            )
            print(
                f"[Gemini] Rate limited — retrying in {delay}s "
                f"(attempt {attempt + 1}/{MAX_RETRIES})"
            )
            time.sleep(delay)

        # Unreachable, but keeps type-checkers happy
        raise RuntimeError("Exhausted retries without a response")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_gemini_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "\n".join(
        str(part.get("text", "")) for part in parts if isinstance(part, dict)
    )


def _parse_json_text(text: str) -> dict[str, Any]:
    stripped = text.strip().strip("`")
    if stripped.startswith("json"):
        stripped = stripped[4:]
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError(f"Gemini returned JSON that is not an object: {type(payload)}")
    return payload


def _guess_mime_type(path: Path) -> str:
    return {
        ".pdf":  "application/pdf",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".txt":  "text/plain",
        ".md":   "text/markdown",
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(path.suffix.lower(), "application/octet-stream")