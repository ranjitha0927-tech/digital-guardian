from flask import Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..models import Report
from ..services.monitoring_service import recalculate_reports

reports_bp = Blueprint("reports", __name__)


@reports_bp.get("/reports/summary")
@jwt_required()
def report_summary():
    parent_id = int(get_jwt_identity())
    recalculate_reports(parent_id)
    report = Report.query.filter_by(parent_id=parent_id, report_type="summary").first()

    if report is None:
        return {
            "weekly_screen_time_hours": 0,
            "restricted_attempts_count": 0,
            "safe_browsing_score": 100,
            "monthly_restricted_attempts": 0,
            "total_safe_searches": 0,
            "parent_notifications_sent": 0,
            "weekly_breakdown": [],
        }

    summary = report.summary_json or {}
    return {
        "weekly_screen_time_hours": report.screen_time_hours,
        "restricted_attempts_count": report.restricted_attempts_count,
        "safe_browsing_score": report.safe_browsing_score,
        "monthly_restricted_attempts": summary.get("monthly_summary", {}).get("restricted_attempts", 0),
        "total_safe_searches": summary.get("monthly_summary", {}).get("safe_searches", 0),
        "parent_notifications_sent": summary.get("monthly_summary", {}).get("notifications_sent", 0),
        "activities_logged": summary.get("monthly_summary", {}).get("activities_logged", 0),
        "weekly_breakdown": summary.get("weekly_breakdown", []),
        "safe_sites": summary.get("safe_sites", []),
        "ai_summary": summary.get("ai_summary", {}),
    }
