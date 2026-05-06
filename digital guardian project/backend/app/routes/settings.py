from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..extensions import db
from ..models import ParentUser, Setting, create_parent_settings, serialize_settings

settings_bp = Blueprint("settings", __name__)


@settings_bp.get("/settings")
@jwt_required()
def get_settings():
    parent_id = int(get_jwt_identity())
    parent = ParentUser.query.get_or_404(parent_id)
    setting = create_parent_settings(parent_id)
    return serialize_settings(setting, parent)


@settings_bp.put("/settings")
@jwt_required()
def update_settings():
    parent_id = int(get_jwt_identity())
    parent = ParentUser.query.get_or_404(parent_id)
    setting = create_parent_settings(parent_id)
    data = request.get_json() or {}

    if "parent_name" in data and data["parent_name"]:
        parent.parent_name = data["parent_name"].strip()
    if "phone_number" in data and data["phone_number"]:
        parent.phone_number = data["phone_number"].strip()
    if "dark_mode" in data:
        setting.dark_mode = bool(data["dark_mode"])
    if "help_email" in data and data["help_email"]:
        setting.help_email = data["help_email"].strip()
    if "security_mode" in data and data["security_mode"]:
        setting.security_mode = data["security_mode"].strip()
    if "notification_enabled" in data:
        setting.notification_enabled = bool(data["notification_enabled"])
    if "email_notifications_enabled" in data:
        setting.email_notifications_enabled = bool(data["email_notifications_enabled"])
    if "emergency_alerts_enabled" in data:
        setting.emergency_alerts_enabled = bool(data["emergency_alerts_enabled"])
    if "weekly_report_day" in data and data["weekly_report_day"]:
        setting.weekly_report_day = data["weekly_report_day"].strip()

    db.session.commit()
    return serialize_settings(setting, parent)
