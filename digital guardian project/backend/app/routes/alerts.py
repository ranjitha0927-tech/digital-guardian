from flask import Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..models import ActivityLog, Alert, MlPredictionLog, NotificationLog, serialize_activity, serialize_alert, serialize_ml_prediction, serialize_notification


alert_bp = Blueprint("alerts_api", __name__)


@alert_bp.get("/alerts-feed")
@jwt_required()
def alerts_feed():
    parent_id = int(get_jwt_identity())
    alerts = Alert.query.filter_by(parent_id=parent_id).order_by(Alert.created_at.desc()).all()
    return [serialize_alert(item) for item in alerts]


@alert_bp.get("/notifications-feed")
@jwt_required()
def notifications_feed():
    parent_id = int(get_jwt_identity())
    items = NotificationLog.query.filter_by(parent_id=parent_id).order_by(NotificationLog.created_at.desc()).all()
    return [serialize_notification(item) for item in items]


@alert_bp.get("/activities-feed")
@jwt_required()
def activities_feed():
    parent_id = int(get_jwt_identity())
    items = ActivityLog.query.filter_by(parent_id=parent_id).order_by(ActivityLog.created_at.desc()).all()
    return [serialize_activity(item) for item in items]


@alert_bp.get("/ml/predictions")
@jwt_required()
def ml_predictions_feed():
    parent_id = int(get_jwt_identity())
    items = MlPredictionLog.query.filter_by(parent_id=parent_id).order_by(MlPredictionLog.created_at.desc()).all()
    return [serialize_ml_prediction(item) for item in items]


@alert_bp.get("/ml/anomalies")
@jwt_required()
def ml_anomalies_feed():
    parent_id = int(get_jwt_identity())
    items = MlPredictionLog.query.filter_by(parent_id=parent_id, anomaly_detected=True).order_by(MlPredictionLog.created_at.desc()).all()
    return [serialize_ml_prediction(item) for item in items]
