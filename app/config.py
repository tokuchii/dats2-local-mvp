from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    # Skip .env in production platforms (Railway) that inject env vars directly.
    _is_platform = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("PORT")
    if _is_platform:
        import logging
        logging.getLogger("dats2.config").info(
            "Platform detected — skipping .env file. DATABASE_URL=%s",
            os.getenv("DATABASE_URL", "(not set)"),
        )
        return
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


REVIEWER_TOKEN = os.getenv("REVIEWER_TOKEN", "").strip()
if not REVIEWER_TOKEN:
    import logging
    logging.getLogger("dats2.config").warning(
        "REVIEWER_TOKEN not set — review/approve actions will be disabled"
    )
try:
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
except ValueError:
    MAX_UPLOAD_MB = 25

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini").strip()
