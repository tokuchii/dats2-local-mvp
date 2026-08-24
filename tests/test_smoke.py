from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

os.environ.setdefault("REVIEWER_TOKEN", "change-this-local-reviewer-token")

from bs4 import BeautifulSoup

from app.main import app  # noqa: E402
from app.db import connect, init_db, get_review_token, get_summary  # noqa: E402
from app.agent import extract_readable_html_text, fetch_url, heuristic_assessment  # noqa: E402
import importlib
import app.config as config_module


def test_llama_ollama_backend_config(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "llama3.1")
    monkeypatch.setenv("LLM_API_KEY", "ollama")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    importlib.reload(config_module)
    assert config_module.LLM_PROVIDER == "ollama"
    assert config_module.LLM_BASE_URL == "http://localhost:11434/v1"
    assert config_module.LLM_MODEL == "llama3.1"
    assert config_module.LLM_API_KEY == "ollama"
    importlib.reload(config_module)


def test_extract_readable_html_text_filters_github_boilerplate():
    html = """
    <html>
      <head><title>GitHub - annaraza/Plot2Map: Plot-to-map comparison of aboveground biomass workflow</title></head>
      <body>
        <nav>GitHub Skip to content Navigation Menu Sign in Appearance settings</nav>
        <main>
          <article class="markdown-body">
            <h1>Plot2Map</h1>
            <p>Plot2Map provides a geospatial workflow for comparing aboveground biomass with yield and field observations.</p>
            <p>The platform supports researchers, extension workers, and agronomists in mapping production patterns and productivity analytics.</p>
          </article>
        </main>
      </body>
    </html>
    """
    text = extract_readable_html_text(BeautifulSoup(html, "html.parser"), "https://github.com/annaraza/Plot2Map")
    assert "Plot2Map provides" in text
    assert "skip to content" not in text.lower()
    assert "sign in" not in text.lower()
    assert "navigation menu" not in text.lower()


def test_heuristic_assessment_ignores_github_shell_text():
    doc = {
        "title": "GitHub - annaraza/Plot2Map: Plot-to-map comparison of aboveground biomass workflow",
        "url": "https://github.com/annaraza/Plot2Map",
        "text": "GitHub - annaraza/Plot2Map: Plot-to-map comparison of aboveground biomass workflow. GitHub Skip to content Navigation Menu Sign in Appearance settings Search / Sign in Sign up. You signed in with another tab or window. Plot2Map provides a geospatial workflow for comparing aboveground biomass with yield and field observations. The platform supports researchers, extension workers, and agronomists in mapping production patterns and productivity analytics.",
        "links": [],
    }
    assessment = heuristic_assessment(doc)
    summary = assessment.core_function.lower()
    assert "github" not in summary
    assert "skip to content" not in summary
    assert "plot2map" in summary and ("provides" in summary or "supports" in summary)


def test_fetch_url_reports_forbidden_sites_cleanly(monkeypatch):
    class FakeResponse:
        status_code = 403
        headers = {"content-type": "text/html"}
        url = "https://ijoear.com/blog/precision-agriculture-maximizing-efficiency-and-minimizing-waste"
        text = "<html>forbidden</html>"
        content = b"<html>forbidden</html>"

        def raise_for_status(self):
            raise RuntimeError("Client error '403 Forbidden' for url 'https://ijoear.com/blog/precision-agriculture-maximizing-efficiency-and-minimizing-waste'")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.agent.httpx.Client", FakeClient)
    try:
        fetch_url("https://ijoear.com/blog/precision-agriculture-maximizing-efficiency-and-minimizing-waste")
    except ValueError as exc:
        assert "403" in str(exc)
        assert "blocked" in str(exc).lower()
    else:
        raise AssertionError("Expected a ValueError for a forbidden URL")


def test_dashboard_and_master_import():
    init_db()
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "DATS 2.0 Observatory" in response.text
        summary = get_summary()
        assert str(summary["systems"]) in response.text
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


def test_submission_status_page_avoids_reload_loop():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM system_versions WHERE candidate_id IS NOT NULL")
        cur.execute("DELETE FROM candidates")
        cur.execute("DELETE FROM submissions")
    text = "AgriFlow is a Philippine digital agriculture inventory and monitoring portal for rice and corn farmers."
    with TestClient(app) as client:
        response = client.post("/submit/text", data={"text": text, "source_url": "", "submitted_by": "Test"}, follow_redirects=True)
        assert response.status_code == 200
        submission_id = client.get("/api/candidates", params={"token": os.environ.get("REVIEWER_TOKEN", "change-this-local-reviewer-token")}).json()[0]["submission_id"]
        page = client.get(f"/submissions/{submission_id}")
        assert page.status_code == 200
        assert "submission_status_changed" in page.text
        assert "window.location.reload()" not in page.text
        assert "setTimeout(function(){ window.location.reload(); }, 1500);" not in page.text


def test_submit_page_has_no_reload_loop():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM system_versions WHERE candidate_id IS NOT NULL")
        cur.execute("DELETE FROM candidates")
        cur.execute("DELETE FROM submissions")
    text = "AgriFlow is a Philippine digital agriculture inventory and monitoring portal for rice and corn farmers."
    with TestClient(app) as client:
        submit_page = client.get("/submit")
        assert submit_page.status_code == 200
        assert "window.location.reload()" not in submit_page.text
        response = client.post("/submit/text", data={"text": text, "source_url": "", "submitted_by": "Test"}, follow_redirects=True)
        assert response.status_code == 200
        candidate_id = client.get("/api/candidates", params={"token": os.environ.get("REVIEWER_TOKEN", "change-this-local-reviewer-token")}).json()[0]["id"]
        detail = client.get(f"/review/{candidate_id}")
        assert detail.status_code == 200
        assert "Editable proposal" in detail.text
        system = client.get("/systems/D2-099")
        assert system.status_code == 200
        assert "Core function" in system.text


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
