from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


RUNS_DIR = Path(os.environ.get("PIPELINE_RUNS_DIR", "runs"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

