from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("REVIEWER_TOKEN", "change-this-local-reviewer-token")

from fastapi.testclient import TestClient

from app.config import UPLOAD_DIR
from app.db import (
    approve_candidate,
    can_delete_approval,
    can_delete_submission,
    connect,
    create_candidate,
    create_submission,
    delete_approval,
    get_candidate,
    get_submission,
    get_system,
    init_db,
    list_audit,
)
from app.main import app

PAYLOAD = {
    "system_name": "Audit delete test system",
    "primary_category": "Farm management & decision support",
    "developer_owner": "Test owner",
    "sector_commodity": ["Rice"],
    "secondary_categories": [],
    "commodity_species_tags": [],
    "value_chain_tags": [],
    "technology_tags": [],
    "livestock_poultry_coverage": "Not dedicated",
    "source_url": "https://example.org/audit-test",
}


def _make_candidate(name: str, uploaded_path: str | None = None) -> tuple[int, int]:
    submission_id = create_submission(
        "file" if uploaded_path else "text",
        source_uri="audit-test.txt",
        uploaded_path=uploaded_path,
        pasted_text=None if uploaded_path else "Audit delete test submission",
        submitted_by="audit-test",
    )
    candidate_id = create_candidate(
        submission_id,
        {**PAYLOAD, "system_name": name},
        [],
        [],
        0.5,
        "heuristic",
    )
    return submission_id, candidate_id


def _cleanup(submission_id: int | None, candidate_id: int | None = None) -> None:
    with connect() as conn:
        cur = conn.cursor()
        if candidate_id:
            cur.execute("DELETE FROM systems WHERE id IN (SELECT system_id FROM system_versions WHERE candidate_id=%s)", (candidate_id,))
            cur.execute("DELETE FROM system_versions WHERE candidate_id=%s", (candidate_id,))
        if submission_id:
            cur.execute("DELETE FROM candidates WHERE submission_id=%s", (submission_id,))
            cur.execute("DELETE FROM submissions WHERE id=%s", (submission_id,))


def test_delete_unapproved_submission_and_upload():
    init_db()
    upload = UPLOAD_DIR / f"audit-{uuid4().hex}.txt"
    upload.write_text("temporary upload", encoding="utf-8")
    submission_id, candidate_id = _make_candidate("Delete upload test", str(upload))
    try:
        assert can_delete_submission(submission_id)[0]
        with TestClient(app) as client:
            audit = client.get("/audit")
            assert audit.status_code == 200
            assert "Delete" in audit.text
            response = client.post(
                f"/audit/submissions/{submission_id}/delete",
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert get_submission(submission_id) is None
        assert get_candidate(candidate_id) is None
        assert not upload.exists()
        event = next(item for item in list_audit() if item["action"] == "delete_submission" and item["entity_id"] == str(submission_id))
        assert event["details"]["status"] == "needs_review"
        assert event["details"]["candidate_ids"] == [candidate_id]
    finally:
        upload.unlink(missing_ok=True)
        _cleanup(submission_id, candidate_id)


def test_delete_approved_new_system():
    init_db()
    submission_id, candidate_id = _make_candidate("Delete approved new system")
    approved = approve_candidate(candidate_id, "audit-test")
    dats2_id = approved["dats2_id"]
    try:
        assert not can_delete_submission(submission_id)[0]
        assert can_delete_approval(candidate_id)[0]
        with TestClient(app) as client:
            audit = client.get("/audit")
            assert f"/audit/approvals/{candidate_id}/delete" in audit.text
            response = client.post(
                f"/audit/approvals/{candidate_id}/delete",
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert get_system(dats2_id) is None
        assert get_submission(submission_id) is None
        assert get_candidate(candidate_id) is None
        event = next(item for item in list_audit() if item["action"] == "delete_approval" and item["entity_id"] == str(candidate_id))
        assert event["details"]["removed_system"] is True
        assert event["details"]["dats2_id"] == dats2_id
    finally:
        _cleanup(submission_id, candidate_id)


def test_delete_approved_merge_restores_previous_version():
    init_db()
    before = get_system("D2-099")
    assert before is not None
    assert before["current_version"] == 1
    submission_id, candidate_id = _make_candidate("Delete approved merge test")
    try:
        approve_candidate(candidate_id, "audit-test", merge_into="D2-099")
        changed = get_system("D2-099")
        assert changed["name"] == "Delete approved merge test"
        assert changed["current_version"] == 2
        assert can_delete_approval(candidate_id)[0]
        with TestClient(app) as client:
            response = client.post(
                f"/audit/approvals/{candidate_id}/delete",
                follow_redirects=False,
            )
        assert response.status_code == 303
        restored = get_system("D2-099")
        assert restored["name"] == before["name"]
        assert restored["current_version"] == 1
        assert get_submission(submission_id) is None
        assert get_candidate(candidate_id) is None
        event = next(item for item in list_audit() if item["action"] == "delete_approval" and item["entity_id"] == str(candidate_id))
        assert event["details"]["removed_system"] is False
        assert event["details"]["restored_version"] == 1
    finally:
        try:
            delete_approval(candidate_id, "audit-test")
        except ValueError:
            pass
        _cleanup(submission_id, candidate_id)


def test_delete_approved_blocks_when_a_newer_system_version_exists():
    init_db()
    first_submission, first_candidate = _make_candidate("First approved delete test")
    second_submission, second_candidate = _make_candidate("Second approved merge test")
    first_system = None
    try:
        first_system = approve_candidate(first_candidate, "audit-test")["dats2_id"]
        approve_candidate(second_candidate, "audit-test", merge_into=first_system)
        assert not can_delete_approval(first_candidate)[0]
        with TestClient(app) as client:
            response = client.post(
                f"/audit/approvals/{first_candidate}/delete",
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert "error=" in response.headers["location"]
        assert get_system(first_system)["current_version"] == 2
    finally:
        if first_system and get_system(first_system):
            try:
                delete_approval(second_candidate, "audit-test")
                delete_approval(first_candidate, "audit-test")
            except ValueError:
                pass
        _cleanup(first_submission, first_candidate)
        _cleanup(second_submission, second_candidate)


def test_delete_missing_submission_returns_error():
    with TestClient(app) as client:
        response = client.post("/audit/submissions/999999/delete", follow_redirects=False)
    assert response.status_code == 303
    assert "error=" in response.headers["location"]


def test_delete_missing_approval_returns_error():
    with TestClient(app) as client:
        response = client.post("/audit/approvals/999999/delete", follow_redirects=False)
    assert response.status_code == 303
    assert "error=" in response.headers["location"]
