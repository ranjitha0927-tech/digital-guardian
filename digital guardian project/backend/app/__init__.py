from flask import Flask, redirect, url_for
from sqlalchemy import inspect, text

from .config import Config
from .extensions import bcrypt, cors, db, jwt, mail
from .models import get_admin_panel_settings, seed_default_admin, seed_default_keywords
from .routes.admin import admin_bp
from .routes.auth import auth_bp
from .routes.browser import browser_bp
from .routes.children import children_bp
from .routes.alerts import alert_bp
from .routes.monitoring import monitoring_bp
from .routes.reports import reports_bp
from .routes.settings import settings_bp
from .services.ml_service import bootstrap_ml_assets


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    bcrypt.init_app(app)
    mail.init_app(app)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(children_bp, url_prefix="/api")
    app.register_blueprint(browser_bp, url_prefix="/api")
    app.register_blueprint(alert_bp, url_prefix="/api")
    app.register_blueprint(monitoring_bp, url_prefix="/api")
    app.register_blueprint(reports_bp, url_prefix="/api")
    app.register_blueprint(settings_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    with app.app_context():
        db.create_all()
        _migrate_legacy_schema()
        seed_default_keywords()
        seed_default_admin(app.config["ADMIN_USERNAME"], app.config["ADMIN_PASSWORD"])
        get_admin_panel_settings()
        bootstrap_ml_assets()

    @app.get("/")
    def home():
        return redirect(url_for("admin.root"))

    @app.get("/api/health")
    def health_check():
        return {"status": "ok", "message": "Digital Guardian backend is running"}

    return app


def _migrate_legacy_schema():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "parent_users" in tables:
        _ensure_column("parent_users", "phone_number", "VARCHAR(40) NOT NULL DEFAULT ''")
    if "child_profiles" in tables:
        _ensure_column("child_profiles", "child_username", "VARCHAR(80) NOT NULL DEFAULT ''")
        _ensure_column("child_profiles", "password_hash", "VARCHAR(255) NOT NULL DEFAULT ''")
        _ensure_column("child_profiles", "screen_time_limit_hours", "FLOAT NOT NULL DEFAULT 2.0")
        _ensure_column("child_profiles", "is_active", "BOOLEAN NOT NULL DEFAULT 1")
    if "browsing_history" in tables:
        _ensure_column("browsing_history", "activity_type", "VARCHAR(40) NOT NULL DEFAULT 'browser_search'")
    if "alerts" in tables:
        _ensure_column("alerts", "activity_id", "INTEGER NULL")
    if "settings" in tables:
        _ensure_column("settings", "notification_enabled", "BOOLEAN NOT NULL DEFAULT 1")
        _ensure_column("settings", "emergency_alerts_enabled", "BOOLEAN NOT NULL DEFAULT 1")
        _ensure_column("settings", "weekly_report_day", "VARCHAR(20) NOT NULL DEFAULT 'Sunday'")
        _ensure_column("settings", "email_notifications_enabled", "BOOLEAN NOT NULL DEFAULT 1")


def _ensure_column(table_name: str, column_name: str, column_sql: str):
    inspector = inspect(db.engine)
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing:
        return
    statement = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
    with db.engine.begin() as connection:
        connection.execute(statement)
