from datetime import datetime

from datetime import datetime, timezone

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..models import (
    ActivityLog,
    Alert,
    BrowsingHistory,
    ChildProfile,
    MlPredictionLog,
    NotificationLog,
    RestrictedKeyword,
    SafeSearchResult,
    serialize_activity,
    serialize_alert,
    serialize_history,
    serialize_ml_prediction,
    serialize_notification,
    serialize_keyword,
    serialize_safe_search_result,
)
from ..services.monitoring_service import (
    analyze_search,
    build_dashboard_payload,
    classify_text,
    emergency_alert,
    log_activity,
)

monitoring_bp = Blueprint("monitoring", __name__)


def _parse_client_datetime(raw_value):
    if not raw_value:
        return datetime.utcnow()
    normalized = raw_value[:-1] + "+00:00" if raw_value.endswith("Z") else raw_value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


@monitoring_bp.post("/monitor/search")
@jwt_required()
def monitor_search():
    parent_id = int(get_jwt_identity())
    data = request.get_json() or {}

    child = ChildProfile.query.filter_by(id=data.get("child_id"), parent_id=parent_id).first()
    if child is None:
        return {"message": "Child profile not found."}, 404

    search_query = (data.get("search_query") or "").strip()
    if not search_query:
        return {"message": "Search query is required."}, 400

    search_time = _parse_client_datetime(data.get("search_time"))

    result = analyze_search(
        parent_id=parent_id,
        child=child,
        search_query=search_query,
        site_url=(data.get("site_url") or "").strip(),
        device_name=(data.get("device_name") or child.device_name).strip(),
        search_time=search_time,
    )
    return result, 201


@monitoring_bp.get("/alerts")
@jwt_required()
def list_alerts():
    parent_id = int(get_jwt_identity())
    alerts = Alert.query.filter_by(parent_id=parent_id).order_by(Alert.created_at.desc()).all()
    return [serialize_alert(alert) for alert in alerts]


@monitoring_bp.get("/history")
@jwt_required()
def list_history():
    parent_id = int(get_jwt_identity())
    items = BrowsingHistory.query.filter_by(parent_id=parent_id).order_by(BrowsingHistory.created_at.desc()).all()
    return [serialize_history(item) for item in items]


@monitoring_bp.get("/safe-results")
@jwt_required()
def list_safe_results():
    parent_id = int(get_jwt_identity())
    items = SafeSearchResult.query.filter_by(parent_id=parent_id).order_by(SafeSearchResult.created_at.desc()).all()
    return [serialize_safe_search_result(item) for item in items]


@monitoring_bp.post("/monitor/activity")
@jwt_required()
def monitor_activity():
    parent_id = int(get_jwt_identity())
    data = request.get_json() or {}

    child = ChildProfile.query.filter_by(id=data.get("child_id"), parent_id=parent_id).first()
    if child is None:
        return {"message": "Child profile not found."}, 404

    event_type = (data.get("event_type") or "app_open").strip().lower()
    title = (data.get("title") or data.get("app_name") or data.get("target_name") or "").strip()
    if not title:
        return {"message": "An app name, title, or target name is required."}, 400

    analysis = classify_text(" ".join(filter(None, [title, data.get("target_url", ""), data.get("details", "")])))
    result = log_activity(
        parent_id=parent_id,
        child=child,
        event_type=event_type,
        title=title,
        target_url=(data.get("target_url") or "").strip(),
        details=(data.get("details") or "").strip(),
        keyword=analysis["keyword"],
        is_restricted=analysis["is_restricted"] or bool(data.get("force_restricted")),
        matched_category=analysis["category"],
        app_name=(data.get("app_name") or "").strip(),
        occurred_at=_parse_client_datetime(data.get("occurred_at")),
    )
    return {
        "message": "Activity logged.",
        "classification": analysis,
        "result": result,
    }, 201


@monitoring_bp.get("/notifications")
@jwt_required()
def list_notifications():
    parent_id = int(get_jwt_identity())
    items = NotificationLog.query.filter_by(parent_id=parent_id).order_by(NotificationLog.created_at.desc()).all()
    return [serialize_notification(item) for item in items]


@monitoring_bp.get("/activities")
@jwt_required()
def list_activities():
    parent_id = int(get_jwt_identity())
    items = ActivityLog.query.filter_by(parent_id=parent_id).order_by(ActivityLog.created_at.desc()).all()
    return [serialize_activity(item) for item in items]


@monitoring_bp.get("/keywords")
@jwt_required()
def list_keywords():
    items = RestrictedKeyword.query.order_by(RestrictedKeyword.created_at.desc()).all()
    return [serialize_keyword(item) for item in items]


@monitoring_bp.post("/emergency")
@monitoring_bp.post("/monitor/emergency")
@jwt_required()
def trigger_emergency():
    parent_id = int(get_jwt_identity())
    data = request.get_json() or {}
    child = ChildProfile.query.filter_by(id=data.get("child_id"), parent_id=parent_id).first()
    if child is None:
        return {"message": "Child profile not found."}, 404
    result = emergency_alert(parent_id, child)
    return {"message": "Emergency alert sent.", "result": result}, 201


@monitoring_bp.get("/dashboard")
@monitoring_bp.get("/monitor/dashboard")
@jwt_required()
def dashboard():
    parent_id = int(get_jwt_identity())
    payload = build_dashboard_payload(parent_id)
    payload["children"] = [
        {
            "id": child.id,
            "child_name": child.child_name,
            "child_username": child.child_username,
            "device_name": child.device_name,
            "screen_time_limit_hours": child.screen_time_limit_hours,
            "is_active": child.is_active,
        }
        for child in ChildProfile.query.filter_by(parent_id=parent_id).order_by(ChildProfile.created_at.desc()).all()
    ]
    payload["alerts"] = [serialize_alert(item) for item in Alert.query.filter_by(parent_id=parent_id).order_by(Alert.created_at.desc()).limit(8).all()]
    payload["notifications"] = [serialize_notification(item) for item in NotificationLog.query.filter_by(parent_id=parent_id).order_by(NotificationLog.created_at.desc()).limit(8).all()]
    payload["history"] = [serialize_history(item) for item in BrowsingHistory.query.filter_by(parent_id=parent_id).order_by(BrowsingHistory.created_at.desc()).limit(10).all()]
    payload["activities"] = [serialize_activity(item) for item in ActivityLog.query.filter_by(parent_id=parent_id).order_by(ActivityLog.created_at.desc()).limit(10).all()]
    payload["children_profiles"] = [
        {
            "id": child.id,
            "child_name": child.child_name,
            "child_username": child.child_username,
            "device_name": child.device_name,
            "screen_time_limit_hours": child.screen_time_limit_hours,
            "is_active": child.is_active,
        }
        for child in ChildProfile.query.filter_by(parent_id=parent_id).order_by(ChildProfile.created_at.desc()).all()
    ]
    return payload


@monitoring_bp.get("/monitor/insights")
@monitoring_bp.get("/insights")
@jwt_required()
def insights():
    parent_id = int(get_jwt_identity())
    payload = build_dashboard_payload(parent_id)
    return {
        "status": "ok",
        "generated_at": datetime.utcnow().isoformat(),
        "ai_summary": payload.get("ai_summary", {}),
    }


@monitoring_bp.get("/ml/predictions")
@jwt_required()
def ml_predictions():
    parent_id = int(get_jwt_identity())
    items = MlPredictionLog.query.filter_by(parent_id=parent_id).order_by(MlPredictionLog.created_at.desc()).all()
    return [serialize_ml_prediction(item) for item in items]


@monitoring_bp.get("/ml/anomalies")
@jwt_required()
def ml_anomalies():
    parent_id = int(get_jwt_identity())
    items = MlPredictionLog.query.filter_by(parent_id=parent_id, anomaly_detected=True).order_by(MlPredictionLog.created_at.desc()).all()
    return [serialize_ml_prediction(item) for item in items]
