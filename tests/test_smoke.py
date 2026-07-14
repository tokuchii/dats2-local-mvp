from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

os.environ.setdefault("REVIEWER_TOKEN", "change-this-local-reviewer-token")

from app.main import app  # noqa: E402
from app.db import connect, init_db  # noqa: E402


def test_dashboard_and_master_import():
    init_db()
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "133" in response.text
        assert "DATS 2.0 Observatory" in response.text
        systems = client.get("/api/systems", params={"search": "DigiSaka", "token": os.environ.get("REVIEWER_TOKEN", "change-this-local-reviewer-token")})
        assert systems.status_code == 200
        assert systems.json()[0]["dats2_id"] == "D2-099"


def test_pasted_text_assessment_and_review():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM system_versions WHERE candidate_id IS NOT NULL")
        cur.execute("DELETE FROM candidates")
        cur.execute("DELETE FROM submissions")
    text = """
    PoultrySense is a Philippine research prototype developed by Example State University.
    The Android application uses IoT temperature, humidity and ammonia sensors to monitor poultry houses.
    It provides alerts to poultry farmers and stores flock and environmental records in a dashboard.
    The prototype was tested in two small farms. No public API or source-code repository was reported.
    """
    with TestClient(app) as client:
        response = client.post("/submit/text", data={"text": text, "source_url": "", "submitted_by": "Test"}, follow_redirects=True)
        assert response.status_code == 200
        assert "Needs Review" in response.text or "Review candidate" in response.text
        candidates = client.get("/api/candidates", params={"token": os.environ.get("REVIEWER_TOKEN", "change-this-local-reviewer-token")}).json()
        assert candidates
        candidate = candidates[0]
        assert "poultry" in candidate["payload"]["livestock_poultry_coverage"].lower()
        detail = client.get(f"/review/{candidate['id']}")
        assert detail.status_code == 200
        assert "Possible duplicates" in detail.text
