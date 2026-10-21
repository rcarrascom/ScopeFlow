import copy
import re
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

import mock_data as data

app = FastAPI()
templates = Jinja2Templates(directory="templates")
templates.env.filters["money"] = lambda v: f"{v:,.2f}" if isinstance(v, (int, float)) else "0.00"

ID_RE = re.compile(r'^[a-zA-Z0-9_]{6,20}$')

def is_valid_id(value: str) -> bool:
    return bool(ID_RE.match(value or ""))

# In-memory working copy - /api/save mutates this, not the module-level data.
# Resets to the original seed set on every restart: no real backing store,
# no risk of accumulating junk edits between sessions.
_projects = copy.deepcopy(data.MOCK_PROJECTS)
_project_by_id = {p["Id"]: p for p in _projects}
_scope_call_by_id = {}
for _p in _projects:
    _calls = _p.get("ScopeCalls__r", {}).get("records", [])
    if _calls:
        _scope_call_by_id[_calls[0]["Id"]] = _calls[0]

LEAD_COLLABORATOR = data.MOCK_COLLABORATORS[0]  # who you land on at "My Pipeline"

SCHEMA_CACHE = {
    "scope_call_picklists": data.SCOPE_CALL_PICKLISTS,
    "qualification": data.QUALIFICATION_META,
    "scope_call_fields": list(data.SCOPE_CALL_FIELD_META.keys()),
    "project_fields": list(data.PROJECT_FIELD_META.keys()),
    "scope_call_field_meta": data.SCOPE_CALL_FIELD_META,
    "project_field_meta": data.PROJECT_FIELD_META,
}


@app.get("/")
@app.get("/Scopion")
async def serve_workspace(request: Request):
    response = templates.TemplateResponse(request=request, name="index.html", context={})
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/schema")
async def get_schema():
    return {"status": "success", "data": SCHEMA_CACHE}


@app.post("/api/shutdown")
async def shutdown_server():
    # Browser tab closed - nothing to tear down server-side (no external
    # session, no real backing store). Left as a no-op so the frontend's
    # unload beacon doesn't need special-casing.
    return {"status": "ok"}


@app.get("/api/collaborators/search")
async def search_collaborators(q: str = "", recommend: bool = False):
    if recommend:
        # No query typed yet - surface a couple of collaborators (not the
        # logged-in lead) so Look Up Collaborator has somewhere to start.
        picks = [u for u in data.MOCK_COLLABORATORS if u["_role"] == "collaborator"][:3]
        return {"status": "success", "data": [{"Id": u["Id"], "Name": u["Name"], "Email": u["Email"]} for u in picks]}
    q = q.strip().lower()
    if len(q) < 2:
        return {"status": "success", "data": []}
    matches = [
        {"Id": u["Id"], "Name": u["Name"], "Email": u["Email"]}
        for u in data.MOCK_COLLABORATORS
        if q in u["Name"].lower() or q in u["Email"].lower()
    ]
    return {"status": "success", "data": matches[:15]}


def _project_matches_collaborator_ids(project: dict, target_ids: set) -> bool:
    members = project.get("Collaborators__r", {}).get("records", [])
    return any(m.get("CollaboratorId") in target_ids for m in members)


def _project_for_response(project: dict, target_ids: set) -> dict:
    # Filters the Collaborators list down to just the requested collaborator
    # id(s) rather than returning the full roster on every project.
    result = copy.deepcopy(project)
    members = result.get("Collaborators__r", {}).get("records", [])
    result["Collaborators__r"]["records"] = [m for m in members if m.get("CollaboratorId") in target_ids]
    return result


@app.get("/api/projects")
async def get_projects(collaborator_ids: str = None):
    if collaborator_ids:
        target_ids = [i.strip() for i in collaborator_ids.split(",") if i.strip()]
        if not target_ids or not all(is_valid_id(i) for i in target_ids):
            return {"status": "error", "message": "Invalid collaborator ID supplied for lookup."}
    else:
        target_ids = [LEAD_COLLABORATOR["Id"]]

    target_set = set(target_ids)
    matched = [_project_for_response(p, target_set) for p in _projects if _project_matches_collaborator_ids(p, target_set)]
    matched.sort(key=lambda p: p.get("LastModifiedDate", ""), reverse=True)
    return {"status": "success", "data": matched}


class ExtraFieldsRequest(BaseModel):
    project_ids: list = []
    project_fields: list = []
    scope_call_ids: list = []
    scope_call_fields: list = []


@app.post("/api/projects/extra-fields")
async def get_extra_fields(req: ExtraFieldsRequest):
    valid_project = set(data.PROJECT_FIELD_META.keys())
    valid_scope_call = set(data.SCOPE_CALL_FIELD_META.keys())
    result = {"project": {}, "scope_call": {}}

    if req.project_ids and req.project_fields:
        ids = [str(i).strip() for i in req.project_ids if str(i).strip()]
        fields = [str(f).strip() for f in req.project_fields if str(f).strip() in valid_project]
        if not ids or not all(is_valid_id(i) for i in ids):
            return {"status": "error", "message": "Invalid Project ID supplied."}
        for project_id in ids:
            project = _project_by_id.get(project_id)
            if not project:
                continue
            result["project"][project_id] = {f: project.get(f) for f in fields}

    if req.scope_call_ids and req.scope_call_fields:
        ids = [str(i).strip() for i in req.scope_call_ids if str(i).strip()]
        fields = [str(f).strip() for f in req.scope_call_fields if str(f).strip() in valid_scope_call]
        if not ids or not all(is_valid_id(i) for i in ids):
            return {"status": "error", "message": "Invalid Scope Call ID supplied."}
        for scope_call_id in ids:
            scope_call = _scope_call_by_id.get(scope_call_id)
            if not scope_call:
                continue
            result["scope_call"][scope_call_id] = {f: scope_call.get(f) for f in fields}

    return {"status": "success", "data": result}


@app.get("/api/analytics")
async def get_analytics():
    """Pipeline-wide analytics: win rate, weighted forecast, risk mix, and
    which qualification signals actually correlate with winning vs losing -
    computed fresh from the current in-memory project set every call."""
    won = [p for p in _projects if p["Stage"] == "6 - Closed Won"]
    lost = [p for p in _projects if p["Stage"] == "7 - Closed Lost"]
    open_projects = [p for p in _projects if "Closed" not in p["Stage"]]

    total_won_value = sum(p.get("DealValue") or 0 for p in won)
    total_won_retainer = sum(p.get("RetainerValue__c") or 0 for p in won)
    avg_won_deal_size = total_won_value / len(won) if won else 0
    win_rate_pct = round(len(won) / (len(won) + len(lost)) * 100, 1) if (won or lost) else 0

    weighted_pipeline_value = sum(
        (p.get("DealValue") or 0) * (p.get("Probability") or 0) / 100 for p in open_projects
    )

    risk_breakdown = {"Green": 0, "Yellow": 0, "Red": 0}
    for p in open_projects:
        calls = p.get("ScopeCalls__r", {}).get("records", [])
        if calls:
            risk = calls[0].get("RiskLevel")
            if risk in risk_breakdown:
                risk_breakdown[risk] += 1

    source_stats = {}
    for p in won + lost:
        source = p.get("LeadSource") or "Unknown"
        bucket = source_stats.setdefault(source, {"won": 0, "lost": 0})
        bucket["won" if p["Stage"] == "6 - Closed Won" else "lost"] += 1
    for source, bucket in source_stats.items():
        total = bucket["won"] + bucket["lost"]
        bucket["rate_pct"] = round(bucket["won"] / total * 100, 1) if total else 0

    lost_reasons = {}
    for p in lost:
        reason = p.get("ClosedReason__c") or "No reason recorded"
        lost_reasons[reason] = lost_reasons.get(reason, 0) + 1
    top_lost_reasons = sorted(
        [{"reason": r, "count": c} for r, c in lost_reasons.items()],
        key=lambda x: x["count"], reverse=True
    )

    # Which qualification signals actually show up more often on won deals
    # than lost ones - a proxy for "what predicts a close" rather than a
    # simple field-fill checklist.
    qual_signal_rates = []
    for field_meta in data.QUALIFICATION_META:
        name, label = field_meta["name"], field_meta["label"]
        won_fill = sum(1 for p in won if p.get(name)) / len(won) * 100 if won else 0
        lost_fill = sum(1 for p in lost if p.get(name)) / len(lost) * 100 if lost else 0
        qual_signal_rates.append({
            "label": label, "won_fill_pct": round(won_fill, 1), "lost_fill_pct": round(lost_fill, 1),
        })

    return {
        "status": "success",
        "data": {
            "total_projects": len(_projects),
            "open_count": len(open_projects),
            "closed_won_count": len(won),
            "closed_lost_count": len(lost),
            "win_rate_pct": win_rate_pct,
            "total_won_value": round(total_won_value, 2),
            "total_won_retainer": round(total_won_retainer, 2),
            "avg_won_deal_size": round(avg_won_deal_size, 2),
            "weighted_pipeline_value": round(weighted_pipeline_value, 2),
            "risk_breakdown": risk_breakdown,
            "source_stats": source_stats,
            "top_lost_reasons": top_lost_reasons,
            "qual_signal_rates": qual_signal_rates,
        },
    }


@app.get("/api/qualification/{project_id}")
async def get_qualification(project_id: str):
    project = _project_by_id.get(project_id)
    if not project:
        return {"status": "error", "message": "Project not found."}
    qualification_data = []
    for field_meta in data.QUALIFICATION_META:
        name = field_meta["name"]
        val = project.get(name)
        if val and isinstance(val, str):
            qualification_data.append({"label": field_meta["label"], "value": val})
    qualification_data.sort(key=lambda x: x["label"])
    return {"status": "success", "data": qualification_data}


class BulkStageRequest(BaseModel):
    project_ids: list = []
    stage: str


@app.post("/api/projects/bulk-stage")
async def bulk_update_stage(req: BulkStageRequest):
    updated = 0
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000+0000")
    for project_id in req.project_ids:
        if not is_valid_id(str(project_id)):
            continue
        project = _project_by_id.get(project_id)
        if not project:
            continue
        project["Stage"] = req.stage
        project["LastModifiedDate"] = now
        updated += 1
    return {"status": "success", "data": {"updated": updated}}


class SaveRequest(BaseModel):
    project_id: str
    scope_call_id: str = None
    project_payload: dict = {}
    scope_call_payload: dict = {}


@app.post("/api/save")
async def save_record(req: SaveRequest):
    if not is_valid_id(req.project_id):
        return {"status": "error", "message": "Invalid Project ID."}
    project = _project_by_id.get(req.project_id)
    if not project:
        return {"status": "error", "message": "Project not found."}

    valid_project = set(data.PROJECT_FIELD_META.keys())
    for field, value in req.project_payload.items():
        if field in valid_project:
            project[field] = value
    project["LastModifiedDate"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000+0000")

    if req.scope_call_id:
        if not is_valid_id(req.scope_call_id):
            return {"status": "error", "message": "Invalid Scope Call ID."}
        scope_call = _scope_call_by_id.get(req.scope_call_id)
        if scope_call:
            valid_scope_call = set(data.SCOPE_CALL_FIELD_META.keys())
            for field, value in req.scope_call_payload.items():
                if field in valid_scope_call:
                    scope_call[field] = value

    return {"status": "success"}


@app.get("/mock-salesforce/opportunity/{project_id}")
async def mock_salesforce_opportunity(request: Request, project_id: str):
    project = _project_by_id.get(project_id)
    if not project:
        return HTMLResponse("<h1>Record not found</h1>", status_code=404)
    scope_calls = project.get("ScopeCalls__r", {}).get("records", [])
    scope_call = scope_calls[0] if scope_calls else {}
    collaborators = [c["Collaborator"]["Name"] for c in project.get("Collaborators__r", {}).get("records", [])]
    return templates.TemplateResponse(
        request=request, name="mock_salesforce_opportunity.html",
        context={"project": project, "scope_call": scope_call, "collaborators": collaborators},
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8004)
