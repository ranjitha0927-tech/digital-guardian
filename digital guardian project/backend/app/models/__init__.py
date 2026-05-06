from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import bcrypt, db


def _serialize_datetime(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str):
        stored = self.password_hash or ""
        if stored.startswith("pbkdf2:") or stored.startswith("scrypt:"):
            return check_password_hash(stored, password)
        try:
            return bcrypt.check_password_hash(stored, password)
        except ValueError:
            return False


class ParentUser(db.Model):
    __tablename__ = "parent_users"

    id = db.Column(db.Integer, primary_key=True)
    parent_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone_number = db.Column(db.String(40), nullable=False, default="")
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    children = db.relationship("ChildProfile", backref="parent", lazy=True, cascade="all, delete-orphan")
    alerts = db.relationship("Alert", backref="parent", lazy=True, cascade="all, delete-orphan")
    reports = db.relationship("Report", backref="parent", lazy=True, cascade="all, delete-orphan")
    settings = db.relationship("Setting", backref="parent", lazy=True, uselist=False, cascade="all, delete-orphan")
    notifications = db.relationship("NotificationLog", backref="parent", lazy=True, cascade="all, delete-orphan")
    safe_search_results = db.relationship("SafeSearchResult", backref="parent", lazy=True, cascade="all, delete-orphan")
    activities = db.relationship("ActivityLog", backref="parent", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str):
        stored = self.password_hash or ""
        if stored.startswith("pbkdf2:") or stored.startswith("scrypt:"):
            return check_password_hash(stored, password)
        try:
            return bcrypt.check_password_hash(stored, password)
        except ValueError:
            return False


class ChildProfile(db.Model):
    __tablename__ = "child_profiles"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent_users.id"), nullable=False)
    child_name = db.Column(db.String(120), nullable=False)
    child_username = db.Column(db.String(80), unique=True, index=True, nullable=False, default="")
    password_hash = db.Column(db.String(255), nullable=False, default="")
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(40), nullable=False)
    grade = db.Column(db.String(80), nullable=False)
    school_name = db.Column(db.String(180), nullable=False)
    parent_contact = db.Column(db.String(80), nullable=False)
    device_name = db.Column(db.String(120), nullable=False)
    screen_time_limit_hours = db.Column(db.Float, nullable=False, default=2.0)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str):
        stored = self.password_hash or ""
        if stored.startswith("pbkdf2:") or stored.startswith("scrypt:"):
            return check_password_hash(stored, password)
        try:
            return bcrypt.check_password_hash(stored, password)
        except ValueError:
            return False


class RestrictedKeyword(db.Model):
    __tablename__ = "restricted_keywords"

    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(120), unique=True, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default="high")
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class BrowsingHistory(db.Model):
    __tablename__ = "browsing_history"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent_users.id"), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("child_profiles.id"), nullable=False)
    search_query = db.Column(db.String(255), nullable=False)
    site_url = db.Column(db.String(255))
    device_name = db.Column(db.String(120))
    activity_type = db.Column(db.String(40), nullable=False, default="browser_search")
    matched_keyword = db.Column(db.String(120))
    matched_category = db.Column(db.String(80))
    is_restricted = db.Column(db.Boolean, default=False, nullable=False)
    search_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    child = db.relationship("ChildProfile", backref="history", lazy=True)


class SafeSearchResult(db.Model):
    __tablename__ = "safe_search_results"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent_users.id"), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("child_profiles.id"), nullable=False)
    history_id = db.Column(db.Integer, db.ForeignKey("browsing_history.id"), nullable=True)
    search_query = db.Column(db.String(255), nullable=False)
    matched_keyword = db.Column(db.String(120))
    search_topic = db.Column(db.String(120))
    is_restricted = db.Column(db.Boolean, default=False, nullable=False)
    recommended_sites = db.Column(db.JSON, nullable=False)
    blocked_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    child = db.relationship("ChildProfile", backref="safe_search_results", lazy=True)
    history = db.relationship("BrowsingHistory", backref="safe_result", lazy=True)


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent_users.id"), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("child_profiles.id"), nullable=False)
    event_type = db.Column(db.String(40), nullable=False)
    app_name = db.Column(db.String(160))
    target_name = db.Column(db.String(160))
    target_url = db.Column(db.String(255))
    keyword = db.Column(db.String(120))
    matched_category = db.Column(db.String(80))
    details = db.Column(db.Text)
    is_restricted = db.Column(db.Boolean, default=False, nullable=False)
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    child = db.relationship("ChildProfile", backref="activities", lazy=True)


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent_users.id"), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("child_profiles.id"), nullable=False)
    history_id = db.Column(db.Integer, db.ForeignKey("browsing_history.id"), nullable=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("activity_logs.id"), nullable=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    child = db.relationship("ChildProfile", backref="alerts", lazy=True)
    history = db.relationship("BrowsingHistory", backref="alert", lazy=True)
    activity = db.relationship("ActivityLog", backref="alert", lazy=True)


class NotificationLog(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent_users.id"), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("child_profiles.id"), nullable=True)
    channel = db.Column(db.String(40), nullable=False, default="sms")
    recipient = db.Column(db.String(80), nullable=False)
    provider = db.Column(db.String(40), nullable=False, default="simulated_twilio")
    trigger_type = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    delivery_status = db.Column(db.String(40), nullable=False, default="sent")
    meta_json = db.Column(db.JSON)
    sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    child = db.relationship("ChildProfile", backref="notifications", lazy=True)


class MlPredictionLog(db.Model):
    __tablename__ = "ml_predictions"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent_users.id"), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("child_profiles.id"), nullable=False)
    history_id = db.Column(db.Integer, db.ForeignKey("browsing_history.id"), nullable=True)
    input_text = db.Column(db.String(255), nullable=False)
    rule_based_label = db.Column(db.String(20), nullable=False, default="safe")
    ml_label = db.Column(db.String(20), nullable=False, default="safe")
    final_label = db.Column(db.String(20), nullable=False, default="safe")
    confidence_score = db.Column(db.Float, nullable=False, default=0.0)
    anomaly_score = db.Column(db.Float, nullable=True)
    anomaly_detected = db.Column(db.Boolean, nullable=False, default=False)
    model_name = db.Column(db.String(80), nullable=False, default="hybrid-logistic-regression")
    feature_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    parent = db.relationship("ParentUser", backref="ml_predictions", lazy=True)
    child = db.relationship("ChildProfile", backref="ml_predictions", lazy=True)
    history = db.relationship("BrowsingHistory", backref="ml_prediction", lazy=True)


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent_users.id"), nullable=False)
    report_type = db.Column(db.String(30), nullable=False)
    week_label = db.Column(db.String(50))
    month_label = db.Column(db.String(50))
    screen_time_hours = db.Column(db.Float, default=0)
    restricted_attempts_count = db.Column(db.Integer, default=0)
    safe_browsing_score = db.Column(db.Float, default=100)
    summary_json = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Setting(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parent_users.id"), unique=True, nullable=False)
    dark_mode = db.Column(db.Boolean, default=False, nullable=False)
    help_email = db.Column(db.String(160), default="support@digitalguardian.local", nullable=False)
    security_mode = db.Column(db.String(40), default="enhanced", nullable=False)
    notification_enabled = db.Column(db.Boolean, default=True, nullable=False)
    email_notifications_enabled = db.Column(db.Boolean, default=True, nullable=False)
    emergency_alerts_enabled = db.Column(db.Boolean, default=True, nullable=False)
    weekly_report_day = db.Column(db.String(20), default="Sunday", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AdminPanelSetting(db.Model):
    __tablename__ = "admin_panel_settings"

    id = db.Column(db.Integer, primary_key=True)
    theme = db.Column(db.String(30), default="pastel-blue", nullable=False)
    security_mode = db.Column(db.String(40), default="strict", nullable=False)
    support_email = db.Column(db.String(160), default="support@digitalguardian.local", nullable=False)
    app_info = db.Column(
        db.String(255),
        default="Digital Guardian Admin Panel",
        nullable=False,
    )
    monitoring_enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AdminAuditLog(db.Model):
    __tablename__ = "admin_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_name = db.Column(db.String(160), nullable=True)
    details = db.Column(db.Text, nullable=True)
    request_path = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    admin = db.relationship("AdminUser", backref="audit_logs", lazy=True)


DEFAULT_KEYWORDS = [
    ("adult", "adult content", "critical"),
    ("adult website", "adult content", "critical"),
    ("adult websites", "adult content", "critical"),
    ("18+", "adult content", "critical"),
    ("porn", "adult content", "critical"),
    ("sex video", "adult content", "critical"),
    ("gambling", "gambling", "high"),
    ("betting", "betting", "high"),
    ("casino", "gambling", "high"),
    ("lottery", "gambling", "high"),
    ("odds", "betting", "medium"),
    ("harmful challenge", "harmful websites", "high"),
    ("self harm", "harmful websites", "critical"),
    ("dark web", "unsafe website", "high"),
    ("unsafe website", "unsafe website", "high"),
    ("unsafe websites", "unsafe website", "high"),
    ("harmful content", "harmful websites", "high"),
]


def seed_default_keywords():
    for keyword, category, severity in DEFAULT_KEYWORDS:
        existing = RestrictedKeyword.query.filter_by(keyword=keyword).first()
        if existing:
            continue
        db.session.add(
            RestrictedKeyword(
                keyword=keyword,
                category=category,
                severity=severity,
            )
        )
    db.session.commit()


def seed_default_admin(username: str = "admin", password: str = "admin123"):
    admin = AdminUser.query.filter_by(username=username).first()
    if admin is None:
        admin = AdminUser(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
    return admin


def get_admin_panel_settings():
    settings = AdminPanelSetting.query.first()
    if settings is None:
        settings = AdminPanelSetting()
        db.session.add(settings)
        db.session.commit()
    return settings


def record_admin_action(
    action: str,
    entity_type: str,
    *,
    admin_id: int | None = None,
    entity_name: str | None = None,
    details: str | None = None,
    request_path: str | None = None,
    ip_address: str | None = None,
):
    log = AdminAuditLog(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_name=entity_name,
        details=details,
        request_path=request_path,
        ip_address=ip_address,
    )
    db.session.add(log)
    db.session.commit()
    return log


def create_parent_settings(parent_id: int):
    setting = Setting.query.filter_by(parent_id=parent_id).first()
    if setting is None:
        setting = Setting(parent_id=parent_id)
        db.session.add(setting)
        db.session.commit()
    return setting


def serialize_child(child: ChildProfile):
    return {
        "id": child.id,
        "parent_id": child.parent_id,
        "child_name": child.child_name,
        "child_username": child.child_username,
        "age": child.age,
        "gender": child.gender,
        "grade": child.grade,
        "school_name": child.school_name,
        "parent_contact": child.parent_contact,
        "device_name": child.device_name,
        "screen_time_limit_hours": child.screen_time_limit_hours,
        "notes": child.notes,
        "is_active": child.is_active,
        "created_at": _serialize_datetime(child.created_at),
    }


def serialize_keyword(keyword: RestrictedKeyword):
    return {
        "id": keyword.id,
        "keyword": keyword.keyword,
        "category": keyword.category,
        "severity": keyword.severity,
        "active": keyword.active,
        "created_at": _serialize_datetime(keyword.created_at),
    }


def serialize_alert(alert: Alert):
    return {
        "id": alert.id,
        "title": alert.title,
        "description": alert.description,
        "severity": alert.severity,
        "status": alert.status,
        "child_name": alert.child.child_name if alert.child else None,
        "created_at": _serialize_datetime(alert.created_at),
    }


def serialize_history(item: BrowsingHistory):
    return {
        "id": item.id,
        "child_id": item.child_id,
        "child_name": item.child.child_name if item.child else None,
        "search_query": item.search_query,
        "site_url": item.site_url,
        "device_name": item.device_name,
        "activity_type": item.activity_type,
        "matched_keyword": item.matched_keyword,
        "matched_category": item.matched_category,
        "is_restricted": item.is_restricted,
        "created_at": _serialize_datetime(item.created_at),
        "search_time": _serialize_datetime(item.search_time),
    }


def serialize_safe_search_result(item: SafeSearchResult):
    return {
        "id": item.id,
        "child_id": item.child_id,
        "child_name": item.child.child_name if item.child else None,
        "search_query": item.search_query,
        "matched_keyword": item.matched_keyword,
        "search_topic": item.search_topic,
        "is_restricted": item.is_restricted,
        "recommended_sites": item.recommended_sites or [],
        "blocked_reason": item.blocked_reason,
        "created_at": _serialize_datetime(item.created_at),
    }


def serialize_activity(item: ActivityLog):
    return {
        "id": item.id,
        "child_id": item.child_id,
        "child_name": item.child.child_name if item.child else None,
        "event_type": item.event_type,
        "app_name": item.app_name,
        "target_name": item.target_name,
        "target_url": item.target_url,
        "keyword": item.keyword,
        "matched_category": item.matched_category,
        "details": item.details,
        "is_restricted": item.is_restricted,
        "occurred_at": _serialize_datetime(item.occurred_at),
        "created_at": _serialize_datetime(item.created_at),
    }


def serialize_notification(item: NotificationLog):
    return {
        "id": item.id,
        "parent_id": item.parent_id,
        "child_id": item.child_id,
        "channel": item.channel,
        "recipient": item.recipient,
        "provider": item.provider,
        "trigger_type": item.trigger_type,
        "title": item.title,
        "message": item.message,
        "delivery_status": item.delivery_status,
        "meta_json": item.meta_json or {},
        "sent_at": _serialize_datetime(item.sent_at),
        "created_at": _serialize_datetime(item.created_at),
    }


def serialize_ml_prediction(item: MlPredictionLog):
    return {
        "id": item.id,
        "parent_id": item.parent_id,
        "child_id": item.child_id,
        "child_name": item.child.child_name if item.child else None,
        "history_id": item.history_id,
        "input_text": item.input_text,
        "rule_based_label": item.rule_based_label,
        "ml_label": item.ml_label,
        "final_label": item.final_label,
        "confidence_score": item.confidence_score,
        "anomaly_score": item.anomaly_score,
        "anomaly_detected": item.anomaly_detected,
        "model_name": item.model_name,
        "feature_json": item.feature_json or {},
        "created_at": _serialize_datetime(item.created_at),
    }


def serialize_settings(setting: Setting, parent: ParentUser):
    return {
        "dark_mode": setting.dark_mode,
        "help_email": setting.help_email,
        "security_mode": setting.security_mode,
        "notification_enabled": setting.notification_enabled,
        "email_notifications_enabled": setting.email_notifications_enabled,
        "emergency_alerts_enabled": setting.emergency_alerts_enabled,
        "weekly_report_day": setting.weekly_report_day,
        "profile": {
            "parent_name": parent.parent_name,
            "email": parent.email,
            "phone_number": parent.phone_number,
        },
    }


def serialize_audit_log(log: AdminAuditLog):
    return {
        "id": log.id,
        "admin_username": log.admin.username if log.admin else None,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_name": log.entity_name,
        "details": log.details,
        "request_path": log.request_path,
        "ip_address": log.ip_address,
        "created_at": _serialize_datetime(log.created_at),
    }


def create_demo_parent(parent_name: str, email: str, password: str):
    user = ParentUser(
        parent_name=parent_name,
        email=email,
        phone_number="",
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
    )
    db.session.add(user)
    db.session.commit()
    create_parent_settings(user.id)
    return user
