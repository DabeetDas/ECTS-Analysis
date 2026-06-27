"""Legacy entrypoint — deploy and run ``pipeline_backend.main`` instead."""

from pipeline_backend.main import app

__all__ = ["app"]
