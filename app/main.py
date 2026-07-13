from __future__ import annotations

import json
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .agent import DATS_CATEGORIES, process_submission
from .config import MAX_UPLOAD_MB, REVIEWER_TOKEN, ROOT, UPLOAD_DIR
from .db import (
    approve_candidate,
    create_submission,
    export_csv_bytes,
    export_xlsx_bytes,
    get_candidate,
    get_submission,
    get_summary,
    get_system,
    init_db,
    list_audit,
    list_candidates,
    list_systems,
    reject_candidate,
    save_candidate_payload,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="DATS 2.0 Local Agentic Dashboard", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "app" / "templates")


def context(request: Request, **kwargs):
    return {"request": request, "categories": DATS_CATEGORIES, **kwargs}


def split_form_tags(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace("|", ";").replace(",", ";").split(";") if part.strip()]


def ensure_reviewer(token: str) -> None:
    if token != REVIEWER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid reviewer token")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "url": "http://localhost:8501"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    summary = get_summary()
    recent = list_systems(limit=8)
    candidates = list_candidates("proposed")[:5]
    return templates.TemplateResponse(request, "dashboard.html", context(request, summary=summary, recent=recent, candidates=candidates))


@app.get("/systems", response_class=HTMLResponse)
def systems_page(
    request: Request,
    search: str = "",
    category: str = "",
    status: str = "",
    commodity: str = "",
    livestock: str = "",
):
    systems = list_systems(search, category, status, commodity, livestock, limit=1000)
    all_systems = list_systems(limit=5000)
    statuses = sorted({s.get("operating_status") for s in all_systems if s.get("operating_status")})
    commodities = sorted({tag for s in all_systems for tag in s.get("commodity_tags", [])})
    livestock_values = sorted({s.get("livestock_coverage") for s in all_systems if s.get("livestock_coverage")})
    return templates.TemplateResponse(
        request,
        "systems.html",
        context(
            request,
            systems=systems,
            filters={"search": search, "category": category, "status": status, "commodity": commodity, "livestock": livestock},
            statuses=statuses,
            commodities=commodities,
            livestock_values=livestock_values,
        ),
    )


@app.get("/systems/{dats2_id}", response_class=HTMLResponse)
def system_detail(request: Request, dats2_id: str):
    system = get_system(dats2_id)
    if not system:
        raise HTTPException(404, "System not found")
    return templates.TemplateResponse(request, "system_detail.html", context(request, system=system))


@app.get("/submit", response_class=HTMLResponse)
def submit_page(request: Request):
    return templates.TemplateResponse(request, "submit.html", context(request))


@app.post("/submit/url")
def submit_url(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    submitted_by: str = Form(""),
):
    submission_id = create_submission("url", source_uri=url.strip(), submitted_by=submitted_by.strip() or None)
    background_tasks.add_task(process_submission, submission_id)
    return RedirectResponse(f"/submissions/{submission_id}", status_code=303)


@app.post("/submit/text")
def submit_text(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    source_url: str = Form(""),
    submitted_by: str = Form(""),
):
    if len(text.strip()) < 40:
        raise HTTPException(400, "Please paste a fuller description or evidence excerpt")
    submission_id = create_submission(
        "text",
        source_uri=source_url.strip() or None,
        pasted_text=text.strip(),
        submitted_by=submitted_by.strip() or None,
    )
    background_tasks.add_task(process_submission, submission_id)
    return RedirectResponse(f"/submissions/{submission_id}", status_code=303)


@app.post("/submit/file")
def submit_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    submitted_by: str = Form(""),
):
    original_name = file.filename or "upload"
    suffix = Path(original_name).suffix.lower()
    allowed = {".pdf", ".txt", ".md", ".csv", ".json"}
    if suffix not in allowed:
        raise HTTPException(400, f"Allowed types: {', '.join(sorted(allowed))}")
    target = UPLOAD_DIR / f"{uuid4().hex}{suffix}"
    size = 0
    with target.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_MB * 1024 * 1024:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, "File exceeds upload limit")
            out.write(chunk)
    submission_id = create_submission(
        "file", source_uri=original_name, uploaded_path=str(target), submitted_by=submitted_by.strip() or None
    )
    background_tasks.add_task(process_submission, submission_id)
    return RedirectResponse(f"/submissions/{submission_id}", status_code=303)


@app.get("/submissions/{submission_id}", response_class=HTMLResponse)
def submission_status(request: Request, submission_id: int):
    submission = get_submission(submission_id)
    if not submission:
        raise HTTPException(404, "Submission not found")
    candidates = [c for c in list_candidates("proposed") if c["submission_id"] == submission_id]
    candidate_id = candidates[0]["id"] if candidates else None
    return templates.TemplateResponse(
        request,
        "submission_status.html",
        context(request, submission=submission, candidate_id=candidate_id),
    )


@app.get("/review", response_class=HTMLResponse)
def review_queue(request: Request, status: str = "proposed"):
    candidates = list_candidates(status)
    return templates.TemplateResponse(request, "review.html", context(request, candidates=candidates, status=status))


@app.get("/review/{candidate_id}", response_class=HTMLResponse)
def review_candidate(request: Request, candidate_id: int):
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(404, "Candidate not found")
    systems = list_systems(limit=5000)
    return templates.TemplateResponse(request, "candidate_detail.html", context(request, candidate=candidate, systems=systems))


@app.post("/review/{candidate_id}/save")
def save_candidate(
    candidate_id: int,
    system_name: str = Form(...),
    acronym: str = Form(""),
    developer_owner: str = Form(""),
    owner_type: str = Form(""),
    sector_commodity: str = Form(""),
    geographic_scope: str = Form(""),
    core_function: str = Form(""),
    technology_channel: str = Form(""),
    primary_users: str = Form(""),
    primary_category: str = Form(...),
    secondary_categories: str = Form(""),
    commodity_species_tags: str = Form(""),
    value_chain_tags: str = Form(""),
    technology_tags: str = Form(""),
    livestock_poultry_coverage: str = Form("Not dedicated"),
    maturity: str = Form(""),
    operating_status: str = Form(""),
    evidence_of_scale: str = Form(""),
    primary_bottleneck: str = Form(""),
    interoperability_score: int = Form(1),
    interoperability_reason: str = Form(""),
    public_source_availability: str = Form(""),
    official_repository_url: str = Form(""),
    public_license: str = Form(""),
    public_api_documentation: str = Form(""),
    machine_readable_export: str = Form(""),
    potential_sinag_role: str = Form(""),
    sinag_priority: str = Form("Medium"),
    recommended_sinag_action: str = Form(""),
    evidence_confidence: str = Form("Medium"),
    overall_confidence: float = Form(0.5),
    source_url: str = Form(""),
):
    candidate = get_candidate(candidate_id)
    if not candidate or candidate["status"] != "proposed":
        raise HTTPException(404, "Proposed candidate not found")
    payload = candidate["payload"]
    payload.update({
        "system_name": system_name.strip(),
        "acronym": acronym.strip() or None,
        "developer_owner": developer_owner.strip() or None,
        "owner_type": owner_type.strip() or None,
        "sector_commodity": split_form_tags(sector_commodity),
        "geographic_scope": geographic_scope.strip() or None,
        "core_function": core_function.strip(),
        "technology_channel": split_form_tags(technology_channel),
        "primary_users": split_form_tags(primary_users),
        "primary_category": primary_category,
        "secondary_categories": split_form_tags(secondary_categories),
        "commodity_species_tags": split_form_tags(commodity_species_tags),
        "value_chain_tags": split_form_tags(value_chain_tags),
        "technology_tags": split_form_tags(technology_tags),
        "livestock_poultry_coverage": livestock_poultry_coverage,
        "maturity": maturity.strip() or None,
        "operating_status": operating_status.strip() or None,
        "evidence_of_scale": evidence_of_scale.strip() or None,
        "primary_bottleneck": primary_bottleneck.strip() or None,
        "interoperability_score": max(0, min(int(interoperability_score), 4)),
        "interoperability_reason": interoperability_reason.strip(),
        "public_source_availability": public_source_availability.strip() or None,
        "official_repository_url": official_repository_url.strip() or None,
        "public_license": public_license.strip() or None,
        "public_api_documentation": public_api_documentation.strip() or None,
        "machine_readable_export": machine_readable_export.strip() or None,
        "potential_sinag_role": potential_sinag_role.strip() or None,
        "sinag_priority": sinag_priority,
        "recommended_sinag_action": recommended_sinag_action.strip() or None,
        "evidence_confidence": evidence_confidence,
        "overall_confidence": max(0.0, min(float(overall_confidence), 1.0)),
        "source_url": source_url.strip() or None,
    })
    save_candidate_payload(candidate_id, payload)
    return RedirectResponse(f"/review/{candidate_id}?saved=1", status_code=303)


@app.post("/review/{candidate_id}/approve")
def approve(
    candidate_id: int,
    reviewer_token: str = Form(...),
    reviewer_name: str = Form("local-reviewer"),
    reviewer_note: str = Form(""),
    merge_into: str = Form(""),
):
    ensure_reviewer(reviewer_token)
    try:
        result = approve_candidate(candidate_id, reviewer_name.strip() or "local-reviewer", reviewer_note.strip() or None, merge_into.strip() or None)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return RedirectResponse(f"/systems/{result['dats2_id']}?approved=1", status_code=303)


@app.post("/review/{candidate_id}/reject")
def reject(
    candidate_id: int,
    reviewer_token: str = Form(...),
    reviewer_name: str = Form("local-reviewer"),
    reviewer_note: str = Form(""),
):
    ensure_reviewer(reviewer_token)
    try:
        reject_candidate(candidate_id, reviewer_name.strip() or "local-reviewer", reviewer_note.strip() or None)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return RedirectResponse("/review", status_code=303)


@app.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request):
    return templates.TemplateResponse(request, "audit.html", context(request, events=list_audit()))


@app.get("/export/current.xlsx")
def export_xlsx():
    return Response(
        export_xlsx_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="DATS_2.0_Current_Database.xlsx"'},
    )


@app.get("/export/current.csv")
def export_csv():
    return Response(
        export_csv_bytes(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="DATS_2.0_Current_Database.csv"'},
    )


@app.get("/api/summary")
def api_summary():
    return get_summary()


@app.get("/api/systems")
def api_systems(search: str = "", category: str = "", status: str = "", commodity: str = "", livestock: str = "", limit: int = 500):
    return list_systems(search, category, status, commodity, livestock, limit)


@app.get("/api/systems/{dats2_id}")
def api_system(dats2_id: str):
    system = get_system(dats2_id)
    if not system:
        raise HTTPException(404, "System not found")
    return system


@app.get("/api/candidates")
def api_candidates(status: str = "proposed"):
    return list_candidates(status)
