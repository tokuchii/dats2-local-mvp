from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

os.environ.setdefault("REVIEWER_TOKEN", "change-this-local-reviewer-token")

from app.main import app  # noqa: E402
from app.db import connect, init_db, get_review_token  # noqa: E402


def test_dashboard_and_master_import():
    init_db()
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "143" in response.text
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
        token = os.environ.get("REVIEWER_TOKEN", "change-this-local-reviewer-token")
        candidates = client.get("/api/candidates", params={"token": token}).json()
        assert candidates
        candidate = candidates[0]
        assert "poultry" in candidate["payload"]["livestock_poultry_coverage"].lower()
        detail = client.get(f"/review/{candidate['id']}")
        assert detail.status_code == 200
        assert "Possible duplicates" in detail.text


def test_reviewer_token_autofilled_and_auth():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM system_versions WHERE candidate_id IS NOT NULL")
        cur.execute("DELETE FROM candidates")
        cur.execute("DELETE FROM submissions")
    text = "FarmTracker is a Philippine mobile app for crop monitoring by Test University."
    with TestClient(app) as client:
        # Submit a candidate
        client.post("/submit/text", data={"text": text, "source_url": "", "submitted_by": "Test"}, follow_redirects=True)
        token = os.environ.get("REVIEWER_TOKEN", "change-this-local-reviewer-token")
        candidates = client.get("/api/candidates", params={"token": token}).json()
        assert candidates, "No candidates after submission"
        cid = candidates[0]["id"]

        # Load the review page — this generates a per-candidate random token
        detail = client.get(f"/review/{cid}")
        assert detail.status_code == 200
        assert 'name="reviewer_token"' in detail.text
        # The hidden field should contain the generated review_token
        assert 'type="hidden" name="reviewer_token"' in detail.text

        # Get the stored review token from DB
        review_token = get_review_token(cid)
        assert review_token, "review_token should be stored in DB"

        # Approve with the correct per-candidate token should succeed (303 redirect)
        resp = client.post(f"/review/{cid}/approve", data={"reviewer_token": review_token, "reviewer_name": "test"}, follow_redirects=False)
        assert resp.status_code == 303

        # Submit another candidate to test reject
        client.post("/submit/text", data={"text": text + " v2", "source_url": "", "submitted_by": "Test"}, follow_redirects=True)
        candidates2 = client.get("/api/candidates", params={"token": token}).json()
        assert candidates2
        cid2 = candidates2[0]["id"]

        # Load review page to generate token for cid2
        client.get(f"/review/{cid2}")
        review_token2 = get_review_token(cid2)

        # Reject with wrong token should fail
        resp_bad = client.post(f"/review/{cid2}/reject", data={"reviewer_token": "wrong-token", "reviewer_name": "test", "reviewer_note": "nope"}, follow_redirects=False)
        assert resp_bad.status_code == 401

        # Reject with correct per-candidate token should succeed
        resp_ok = client.post(f"/review/{cid2}/reject", data={"reviewer_token": review_token2, "reviewer_name": "test", "reviewer_note": "rejected"}, follow_redirects=False)
        assert resp_ok.status_code == 303
