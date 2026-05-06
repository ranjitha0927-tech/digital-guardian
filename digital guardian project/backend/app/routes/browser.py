from datetime import datetime, timezone

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..models import ChildProfile, SafeSearchResult, serialize_history, serialize_safe_search_result
from ..services.monitoring_service import analyze_search, build_dashboard_payload


browser_bp = Blueprint("browser", __name__)


def _parse_client_datetime(raw_value):
    if not raw_value:
        return datetime.utcnow()
    normalized = raw_value[:-1] + "+00:00" if raw_value.endswith("Z") else raw_value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


@browser_bp.post("/browser/search")
@jwt_required()
def browser_search():
    parent_id = int(get_jwt_identity())
    data = request.get_json() or {}
    child = ChildProfile.query.filter_by(id=data.get("child_id"), parent_id=parent_id).first()
    if child is None:
        return {"message": "Child profile not found."}, 404
    search_query = (data.get("search_query") or "").strip()
    if not search_query:
        return {"message": "Search query is required."}, 400
    result = analyze_search(
        parent_id=parent_id,
        child=child,
        search_query=search_query,
        site_url=(data.get("site_url") or "").strip(),
        device_name=(data.get("device_name") or child.device_name).strip(),
        search_time=_parse_client_datetime(data.get("search_time")),
    )
    return result, 201


@browser_bp.get("/browser/history")
@jwt_required()
def browser_history():
    parent_id = int(get_jwt_identity())
    payload = build_dashboard_payload(parent_id)
    return payload.get("history", [])


@browser_bp.get("/browser/safe-results")
@jwt_required()
def browser_safe_results():
    parent_id = int(get_jwt_identity())
    items = SafeSearchResult.query.filter_by(parent_id=parent_id).order_by(SafeSearchResult.created_at.desc()).all()
    return [serialize_safe_search_result(item) for item in items]


@browser_bp.get("/browser/dashboard")
@jwt_required()
def browser_dashboard():
    parent_id = int(get_jwt_identity())
    return build_dashboard_payload(parent_id)
