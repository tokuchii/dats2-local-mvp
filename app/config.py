from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/dats2")
MASTER_XLSX = DATA_DIR / "DATS_2.0_Philippines_Master_2026.xlsx"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "").strip()
REVIEWER_TOKEN = os.getenv("REVIEWER_TOKEN", "").strip()
if not REVIEWER_TOKEN:
    raise RuntimeError("REVIEWER_TOKEN must be set in .env — refusing to start with an empty token")
try:
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
except ValueError:
    MAX_UPLOAD_MB = 25

# OpenAI configuration (production-ready alternative to Ollama)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o").strip()
