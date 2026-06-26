from __future__ import annotations
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from pipeline_backend.config import RUNS_DIR
from pipeline_backend.schemas import PipelineResult


# ── local store (unchanged) ───────────────────────────────────────────────────

class RunStore:
    def __init__(self, base_dir: Path = RUNS_DIR) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_run(self) -> str:
        run_id = uuid.uuid4().hex
        self.run_dir(run_id).mkdir(parents=True)
        self.write_json(run_id, "result.json", PipelineResult(run_id=run_id).model_dump())
        return run_id

    def run_dir(self, run_id: str) -> Path:
        return self.base_dir / safe_run_id(run_id)

    def save_upload(self, run_id: str, source: Path, target_name: str) -> str:
        destination = self.run_dir(run_id) / target_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        return str(destination)

    def write_bytes(self, run_id: str, filename: str, data: bytes) -> str:
        destination = self.run_dir(run_id) / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return str(destination)

    def write_json(self, run_id: str, filename: str, payload: Any) -> Path:
        path = self.run_dir(run_id) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def read_json(self, run_id: str, filename: str) -> dict[str, Any]:
        path = self.run_dir(run_id) / filename
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}

    def read_result(self, run_id: str) -> PipelineResult:
        payload = self.read_json(run_id, "result.json")
        return PipelineResult(**payload) if payload else PipelineResult(run_id=run_id)

    def write_result(self, result: PipelineResult) -> None:
        self.write_json(result.run_id, "result.json", result.model_dump())

    def read_bytes(self, run_id: str, filename: str) -> bytes:
        return (self.run_dir(run_id) / filename).read_bytes()

    def list_runs(self) -> list[str]:
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]


# ── Backblaze B2 backend ──────────────────────────────────────────────────────

class B2RunStore:
    """Drop-in replacement for RunStore backed by Backblaze B2."""

    def __init__(self, endpoint: str, bucket: str, key_id: str, application_key: str) -> None:
        self.bucket = bucket
        self.s3 = boto3.client(
            service_name="s3",
            endpoint_url=endpoint,            # e.g. https://s3.us-west-004.backblazeb2.com
            aws_access_key_id=key_id,         # B2 keyID
            aws_secret_access_key=application_key,  # B2 applicationKey
            config=Config(signature_version="s3v4"),
        )

    def _key(self, run_id: str, filename: str) -> str:
        full_prefix = f"runs/{safe_run_id(run_id)}/"
        if filename.startswith(full_prefix):
            return filename
        return f"runs/{safe_run_id(run_id)}/{filename}"

    def create_run(self) -> str:
        run_id = uuid.uuid4().hex
        self.write_json(run_id, "result.json", PipelineResult(run_id=run_id).model_dump())
        return run_id

    def save_upload(self, run_id: str, source: Path, target_name: str) -> str:
        key = self._key(run_id, target_name)
        self.s3.upload_file(str(source), self.bucket, key)
        return key

    def write_bytes(self, run_id: str, filename: str, data: bytes) -> str:
        key = self._key(run_id, filename)
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    def write_json(self, run_id: str, filename: str, payload: Any) -> str:
        data = json.dumps(payload, indent=2).encode("utf-8")
        return self.write_bytes(run_id, filename, data)

    def read_json(self, run_id: str, filename: str) -> dict[str, Any]:
        try:
            obj = self.s3.get_object(Bucket=self.bucket, Key=self._key(run_id, filename))
            payload = json.loads(obj["Body"].read().decode("utf-8"))
            return payload if isinstance(payload, dict) else {}
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return {}
            raise

    def read_result(self, run_id: str) -> PipelineResult:
        payload = self.read_json(run_id, "result.json")
        return PipelineResult(**payload) if payload else PipelineResult(run_id=run_id)

    def write_result(self, result: PipelineResult) -> None:
        self.write_json(result.run_id, "result.json", result.model_dump())

    def read_bytes(self, run_id: str, filename: str) -> bytes:
        try:
            obj = self.s3.get_object(Bucket=self.bucket, Key=self._key(run_id, filename))
            return obj["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                raise FileNotFoundError(f"Object not found: {filename}") from e
            raise

    def list_runs(self) -> list[str]:
        paginator = self.s3.get_paginator("list_objects_v2")
        run_ids: list[str] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix="runs/", Delimiter="/"):
            for prefix in page.get("CommonPrefixes", []):
                run_ids.append(prefix["Prefix"].split("/")[1])
        return run_ids


# ── factory ───────────────────────────────────────────────────────────────────

def get_run_store() -> RunStore | B2RunStore:
    """
    Returns B2RunStore when B2_* env vars are present, else local RunStore.
    Local dev works with no config changes.
    """
    from dotenv import load_dotenv
    load_dotenv()
    endpoint = os.getenv("B2_ENDPOINT")
    bucket = os.getenv("B2_BUCKET")
    key_id = os.getenv("B2_KEY_ID")
    application_key = os.getenv("B2_APPLICATION_KEY")

    if all([endpoint, bucket, key_id, application_key]):
        return B2RunStore(
            endpoint=endpoint,
            bucket=bucket,
            key_id=key_id,
            application_key=application_key,
        )

    return RunStore()


# ── helpers ───────────────────────────────────────────────────────────────────

def safe_run_id(run_id: str) -> str:
    cleaned = "".join(ch for ch in run_id if ch.isalnum() or ch in {"_", "-"})
    if not cleaned:
        raise ValueError("Invalid run id")
    return cleaned

