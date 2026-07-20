from __future__ import annotations

import hmac
import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .agent import DATS_CATEGORIES, process_submission
from .config import MAX_UPLOAD_MB, REVIEWER_TOKEN, ROOT, UPLOAD_DIR
from .sse import publish, subscribe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("dats2")
from .db import (
    approve_candidate,
    count_candidates,
    count_systems,
    create_submission,
    export_csv_bytes,
    export_xlsx_bytes,
    get_candidate,
    get_filter_values,
    get_submission,
    get_review_token,
    get_summary,
    get_system,
    init_db,
    list_audit,
    list_candidates,
    list_systems,
    reject_candidate,
    save_candidate_payload,
    set_review_token,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    raw_db = os.getenv("DATABASE_URL", "(not set)")
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(raw_db)
    redacted = urlunparse(parsed._replace(netloc=parsed.netloc.replace(parsed.password, "•••") if parsed.password else parsed.netloc))
    log.info("Starting DATS 2.0 — DATABASE_URL=%s", redacted)
    try:
        init_db()
        log.info("Database initialized successfully")
    except Exception:
        log.exception("Database initialization failed")
        raise
    yield


app = FastAPI(title="DATS 2.0 Local Agentic Dashboard", version="1.0.0", lifespan=lifespan)


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("x-forwarded-proto") == "https":
            request.scope["scheme"] = "https"
        return await call_next(request)


class StaticCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
        return response


app.add_middleware(ProxyHeadersMiddleware)
app.add_middleware(StaticCacheMiddleware)

static_dir = ROOT / "app" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=ROOT / "app" / "templates")


def _safe_url(value: str | None) -> str:
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    return ""


templates.env.filters["safe_url"] = _safe_url


def _fmt_time(value: str | None) -> str:
    if not value:
        return ""
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone()
        return local.strftime("%b %d, %Y %I:%M %p")
    except (ValueError, TypeError):
        return value


templates.env.filters["fmt_time"] = _fmt_time


def context(request: Request, **kwargs):
    masked = "•" * len(REVIEWER_TOKEN) if REVIEWER_TOKEN else ""
    return {"request": request, "categories": DATS_CATEGORIES, "proposed_count": count_candidates("proposed"), "reviewer_token": REVIEWER_TOKEN, "reviewer_token_display": masked, **kwargs}


def split_form_tags(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace("|", ";").replace(",", ";").split(";") if part.strip()]


def ensure_reviewer(token: str) -> None:
    if not hmac.compare_digest(token, REVIEWER_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid reviewer token")


def ensure_api_auth(request: Request) -> None:
    token = request.query_params.get("token", "")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not hmac.compare_digest(token, REVIEWER_TOKEN):
        raise HTTPException(status_code=401, detail="API token required. Pass ?token=... or Authorization: Bearer ...")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/favicon.ico")
def favicon():
    return RedirectResponse("/static/favicon.svg", status_code=301)


@app.get("/api/events")
async def sse_events():
    return StreamingResponse(
        subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    summary = get_summary()
    recent = list_systems(limit=3)
    total_candidates = count_candidates("proposed")
    candidates = list_candidates("proposed")[:5]
    return templates.TemplateResponse(request, "dashboard.html", context(request, summary=summary, recent=recent, candidates=candidates, total_candidates=total_candidates))


@app.get("/systems", response_class=HTMLResponse)
def systems_page(
    request: Request,
    search: str = "",
    category: str = "",
    status: str = "",
    commodity: str = "",
    livestock: str = "",
    page: int = 1,
):
    per_page = 50
    total = count_systems(search, category, status, commodity, livestock)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    systems = list_systems(search, category, status, commodity, livestock, limit=per_page, offset=(page - 1) * per_page)
    filters = get_filter_values()
    return templates.TemplateResponse(
        request,
        "systems.html",
        context(
            request,
            systems=systems,
            filters={"search": search, "category": category, "status": status, "commodity": commodity, "livestock": livestock},
            statuses=filters["statuses"],
            commodities=filters["commodities"],
            livestock_values=filters["livestock"],
            page=page,
            total_pages=total_pages,
            total=total,
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
    publish("submission_created", {"submission_id": submission_id, "source_type": "url"})
    publish("proposed_count_changed", {"count": count_candidates("proposed")})
    return RedirectResponse(f"/submissions/{submission_id}?success=URL+submitted+for+assessment", status_code=303)


@app.post("/submit/text")
def submit_text(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    source_url: str = Form(""),
    submitted_by: str = Form(""),
):
    if len(text.strip()) < 40:
        raise HTTPException(400, "Please paste a fuller description or evidence excerpt")
    if len(text.strip()) > 100_000:
        raise HTTPException(400, "Text exceeds 100,000 character limit")
    submission_id = create_submission(
        "text",
        source_uri=source_url.strip() or None,
        pasted_text=text.strip(),
        submitted_by=submitted_by.strip() or None,
    )
    background_tasks.add_task(process_submission, submission_id)
    publish("submission_created", {"submission_id": submission_id, "source_type": "text"})
    publish("proposed_count_changed", {"count": count_candidates("proposed")})
    return RedirectResponse(f"/submissions/{submission_id}?success=Text+submitted+for+assessment", status_code=303)


@app.post("/submit/file")
def submit_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    submitted_by: str = Form(""),
):
    original_name = file.filename or "upload"
    suffix = Path(original_name).suffix.lower()
    allowed = {".pdf", ".txt", ".md", ".csv", ".json", ".xlsx", ".xls"}
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
    publish("submission_created", {"submission_id": submission_id, "source_type": "file"})
    publish("proposed_count_changed", {"count": count_candidates("proposed")})
    return RedirectResponse(f"/submissions/{submission_id}?success=File+uploaded+for+assessment", status_code=303)


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
    counts = {s: count_candidates(s) for s in ("proposed", "approved", "rejected")}
    return templates.TemplateResponse(request, "review.html", context(request, candidates=candidates, status=status, counts=counts))


@app.get("/review/{candidate_id}", response_class=HTMLResponse)
def review_candidate(request: Request, candidate_id: int):
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(404, "Candidate not found")
    systems = list_systems(limit=5000)
    review_token = get_review_token(candidate_id)
    if not review_token:
        review_token = secrets.token_hex(24)
        set_review_token(candidate_id, review_token)
    return templates.TemplateResponse(request, "candidate_detail.html", context(request, candidate=candidate, systems=systems, review_token=review_token))


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
    main_scaling_strength: str = Form(""),
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
        "main_scaling_strength": main_scaling_strength.strip() or None,
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
    publish("candidate_saved", {"candidate_id": candidate_id})
    return RedirectResponse(f"/review/{candidate_id}?success=Candidate+saved", status_code=303)


@app.post("/review/{candidate_id}/approve")
def approve(
    candidate_id: int,
    reviewer_token: str = Form(...),
    reviewer_name: str = Form("local-reviewer"),
    reviewer_note: str = Form(""),
    merge_into: str = Form(""),
):
    stored_token = get_review_token(candidate_id)
    if not stored_token or not hmac.compare_digest(reviewer_token, stored_token):
        raise HTTPException(status_code=401, detail="Invalid reviewer token")
    try:
        result = approve_candidate(candidate_id, reviewer_name.strip() or "local-reviewer", reviewer_note.strip() or None, merge_into.strip() or None)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    publish("system_approved", {"dats2_id": result["dats2_id"], "version": result["version"]})
    publish("proposed_count_changed", {"count": count_candidates("proposed")})
    return RedirectResponse(f"/systems/{result['dats2_id']}?success=System+approved+successfully", status_code=303)


@app.post("/review/{candidate_id}/reject")
def reject(
    candidate_id: int,
    reviewer_token: str = Form(...),
    reviewer_name: str = Form("local-reviewer"),
    reviewer_note: str = Form(""),
):
    stored_token = get_review_token(candidate_id)
    if not stored_token or not hmac.compare_digest(reviewer_token, stored_token):
        raise HTTPException(status_code=401, detail="Invalid reviewer token")
    try:
        reject_candidate(candidate_id, reviewer_name.strip() or "local-reviewer", reviewer_note.strip() or None)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    publish("candidate_rejected", {"candidate_id": candidate_id})
    publish("proposed_count_changed", {"count": count_candidates("proposed")})
    return RedirectResponse("/review?success=Candidate+rejected", status_code=303)


@app.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request):
    return templates.TemplateResponse(request, "audit.html", context(request, events=list_audit()))


@app.get("/export/current.xlsx")
def export_xlsx(request: Request):
    return Response(
        export_xlsx_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="DATS_2.0_Current_Database.xlsx"'},
    )


@app.get("/export/current.csv")
def export_csv(request: Request):
    return Response(
        export_csv_bytes(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="DATS_2.0_Current_Database.csv"'},
    )


@app.get("/api/summary")
def api_summary(request: Request):
    ensure_api_auth(request)
    return get_summary()


@app.get("/api/systems")
def api_systems(request: Request, search: str = "", category: str = "", status: str = "", commodity: str = "", livestock: str = "", limit: int = 500):
    ensure_api_auth(request)
    return list_systems(search, category, status, commodity, livestock, limit)


@app.get("/api/systems/{dats2_id}")
def api_system(request: Request, dats2_id: str):
    ensure_api_auth(request)
    system = get_system(dats2_id)
    if not system:
        raise HTTPException(404, "System not found")
    return system


@app.get("/api/candidates")
def api_candidates(request: Request, status: str = "proposed"):
    ensure_api_auth(request)
    return list_candidates(status)


@app.get("/api/proposed-count")
def api_proposed_count():
    return {"count": count_candidates("proposed")}
