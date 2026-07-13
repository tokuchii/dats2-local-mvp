from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

host = os.getenv("DATS2_HOST", "127.0.0.1")
port = int(os.getenv("DATS2_PORT", "8501"))

if __name__ == "__main__":
    print(f"\nDATS 2.0 Local Dashboard: http://localhost:{port}\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
