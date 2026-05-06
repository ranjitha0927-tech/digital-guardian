import json
from datetime import datetime
from functools import wraps

from sqlalchemy import or_
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ..extensions import db
from ..models import (
    AdminUser,
    AdminPanelSetting,
    AdminAuditLog,
    Alert,
    ActivityLog,
    BrowsingHistory,
    ChildProfile,
    MlPredictionLog,
    NotificationLog,
    ParentUser,
    Report,
    RestrictedKeyword,
    SafeSearchResult,
    create_parent_settings,
    get_admin_panel_settings,
    record_admin_action,
    serialize_audit_log,
    serialize_ml_prediction,
)
from ..services.ai_risk_service import build_parent_ai_insights
from ..services.monitoring_service import _estimate_screen_time_hours

admin_bp = Blueprint("admin", __name__, template_folder="../templates", static_folder="../static")


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def build_dashboard_metrics():
    total_parents = ParentUser.query.count()
    total_children = ChildProfile.query.count()
    total_restricted = BrowsingHistory.query.filter_by(is_restricted=True).count()
    total_alerts = Alert.query.count()
    total_notifications = NotificationLog.query.count()
    total_safe_results = SafeSearchResult.query.count()
    total_activities = ActivityLog.query.count()
    total_reports = Report.query.count()
    history_total = BrowsingHistory.query.count()
    safe_score = 100 if history_total == 0 else round(((history_total - total_restricted) / history_total) * 100, 1)
    settings = get_admin_panel_settings()

    recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
    recent_history = BrowsingHistory.query.order_by(BrowsingHistory.created_at.desc()).limit(8).all()
    recent_safe_results = SafeSearchResult.query.order_by(SafeSearchResult.created_at.desc()).limit(8).all()
    recent_notifications = NotificationLog.query.order_by(NotificationLog.created_at.desc()).limit(8).all()
    recent_ml_predictions = MlPredictionLog.query.order_by(MlPredictionLog.created_at.desc()).limit(8).all()
    recent_audit_logs = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).limit(8).all()
    weekly_reports = Report.query.order_by(Report.created_at.desc()).limit(6).all()

    trend_labels = []
    safe_trend = []
    restricted_trend = []
    for report in reversed(weekly_reports):
        summary = report.summary_json or {}
        breakdown = summary.get("weekly_breakdown", [])
        safe_total = sum(item.get("safe", 0) for item in breakdown)
        restricted_total = sum(item.get("restricted", 0) for item in breakdown)
        trend_labels.append(report.month_label or report.week_label or f"Report {report.id}")
        safe_trend.append(safe_total)
        restricted_trend.append(restricted_total)

    category_breakdown = {}
    for item in BrowsingHistory.query.filter(BrowsingHistory.matched_category.isnot(None)).all():
        category = item.matched_category or "Other"
        category_breakdown[category] = category_breakdown.get(category, 0) + 1

    parent_ai_insights = []
    for parent in ParentUser.query.order_by(ParentUser.created_at.asc()).all():
        parent_histories = BrowsingHistory.query.filter_by(parent_id=parent.id).all()
        parent_activities = ActivityLog.query.filter_by(parent_id=parent.id).all()
        parent_alerts = Alert.query.filter_by(parent_id=parent.id).all()
        parent_safe_results = SafeSearchResult.query.filter_by(parent_id=parent.id).all()
        parent_children = ChildProfile.query.filter_by(parent_id=parent.id).all()
        screen_time_by_child = {
            child.id: _estimate_screen_time_hours(
                [item for item in parent_histories if item.child_id == child.id],
                [item for item in parent_activities if item.child_id == child.id],
            )
            for child in parent_children
        }
        parent_ai_insights.append(
            build_parent_ai_insights(
                parent.id,
                parent_children,
                parent_histories,
                parent_activities,
                parent_alerts,
                parent_safe_results,
                screen_time_by_child,
            )
        )

    top_parent_name = "N/A"
    parent_counts = {}
    for parent_id, in db.session.query(BrowsingHistory.parent_id).all():
        parent_counts[parent_id] = parent_counts.get(parent_id, 0) + 1
    if parent_counts:
        top_parent_id = max(parent_counts, key=parent_counts.get)
        top_parent = ParentUser.query.get(top_parent_id)
        if top_parent:
            top_parent_name = top_parent.parent_name

    flattened_child_insights = [
        child
        for insight in parent_ai_insights
        for child in insight.get("children", [])
    ]
    avg_risk_score = round(
        sum(item["risk_score"] for item in flattened_child_insights) / max(len(flattened_child_insights), 1),
        2,
    ) if flattened_child_insights else 0
    anomaly_total = sum(item.get("anomaly_count", 0) for item in flattened_child_insights)
    highest_risk_child = max(flattened_child_insights, key=lambda item: item["risk_score"]) if flattened_child_insights else None

    return {
        "total_parents": total_parents,
        "total_children": total_children,
        "total_restricted": total_restricted,
        "total_alerts": total_alerts,
        "total_notifications": total_notifications,
        "total_safe_results": total_safe_results,
        "total_activities": total_activities,
        "total_reports": total_reports,
        "safe_score": safe_score,
        "monitoring_status": "Active" if settings.monitoring_enabled else "Paused",
        "recent_alerts": recent_alerts,
        "recent_history": recent_history,
        "recent_safe_results": recent_safe_results,
        "recent_notifications": recent_notifications,
        "recent_ml_predictions": recent_ml_predictions,
        "recent_audit_logs": recent_audit_logs,
        "trend_labels": json.dumps(trend_labels),
        "safe_trend": json.dumps(safe_trend),
        "restricted_trend": json.dumps(restricted_trend),
        "category_labels": json.dumps(list(category_breakdown.keys())),
        "category_values": json.dumps(list(category_breakdown.values())),
        "settings": settings,
        "top_parent_name": top_parent_name,
        "avg_risk_score": avg_risk_score,
        "anomaly_total": anomaly_total,
        "highest_risk_child_name": highest_risk_child["child_name"] if highest_risk_child else "N/A",
        "highest_risk_child_score": highest_risk_child["risk_score"] if highest_risk_child else 0,
        "child_ai_insights": flattened_child_insights[:8],
    }


def log_admin_action(action: str, entity_type: str, *, entity_name: str | None = None, details: str | None = None):
    admin_id = session.get("admin_id")
    if not admin_id:
        return None
    return record_admin_action(
        action=action,
        entity_type=entity_type,
        admin_id=admin_id,
        entity_name=entity_name,
        details=details,
        request_path=request.path,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
    )


@admin_bp.get("/")
def root():
    if "admin_id" in session:
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("admin.login"))


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if "admin_id" in session:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        admin = AdminUser.query.filter_by(username=username, is_active=True).first()
        if admin and admin.check_password(password):
            admin.last_login_at = datetime.utcnow()
            db.session.commit()
            session["admin_id"] = admin.id
            session["admin_username"] = admin.username
            log_admin_action("login", "admin_user", entity_name=admin.username, details="Admin signed in.")
            flash("Welcome back to the Digital Guardian admin console.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("admin.dashboard"))

        flash("Invalid admin username or password.", "error")

    return render_template("admin/login.html")


@admin_bp.get("/logout")
@admin_required
def logout():
    username = session.get("admin_username")
    if session.get("admin_id"):
        log_admin_action("logout", "admin_user", entity_name=username, details="Admin signed out.")
    session.clear()
    flash("Admin session ended successfully.", "success")
    return redirect(url_for("admin.login"))


@admin_bp.get("/dashboard")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html", metrics=build_dashboard_metrics())


@admin_bp.get("/audit-logs")
@admin_required
def audit_logs():
    logs = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).limit(200).all()
    return render_template("admin/audit_logs.html", logs=logs)


@admin_bp.get("/api/summary")
@admin_required
def api_summary():
    metrics = build_dashboard_metrics()
    return {
        "status": "ok",
        "generated_at": datetime.utcnow().isoformat(),
        "metrics": {
            "total_parents": metrics["total_parents"],
            "total_children": metrics["total_children"],
            "total_restricted": metrics["total_restricted"],
            "total_alerts": metrics["total_alerts"],
            "total_notifications": metrics["total_notifications"],
            "total_safe_results": metrics["total_safe_results"],
            "total_activities": metrics["total_activities"],
            "total_reports": metrics["total_reports"],
            "safe_score": metrics["safe_score"],
            "monitoring_status": metrics["monitoring_status"],
            "top_parent_name": metrics["top_parent_name"],
            "avg_risk_score": metrics["avg_risk_score"],
            "anomaly_total": metrics["anomaly_total"],
            "highest_risk_child_name": metrics["highest_risk_child_name"],
            "highest_risk_child_score": metrics["highest_risk_child_score"],
        },
    }


@admin_bp.get("/api/health")
@admin_required
def api_health():
    settings_obj = get_admin_panel_settings()
    return {
        "status": "ok",
        "database": "connected",
        "monitoring_enabled": settings_obj.monitoring_enabled,
        "admin_theme": settings_obj.theme,
        "server_time_utc": datetime.utcnow().isoformat(),
    }


@admin_bp.get("/api/audit-logs")
@admin_required
def api_audit_logs():
    logs = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).limit(100).all()
    return {
        "status": "ok",
        "count": len(logs),
        "logs": [serialize_audit_log(log) for log in logs],
    }


@admin_bp.get("/api/ml-predictions")
@admin_required
def api_ml_predictions():
    rows = MlPredictionLog.query.order_by(MlPredictionLog.created_at.desc()).limit(150).all()
    return {"status": "ok", "count": len(rows), "predictions": [serialize_ml_prediction(row) for row in rows]}


@admin_bp.get("/parents")
@admin_required
def parents():
    search = request.args.get("search", "").strip()
    query = ParentUser.query
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(ParentUser.parent_name.ilike(like), ParentUser.email.ilike(like))
        )
    parents_list = query.order_by(ParentUser.created_at.desc()).all()
    return render_template("admin/parents.html", parents=parents_list, search=search)


@admin_bp.route("/parents/new", methods=["GET", "POST"])
@admin_required
def create_parent():
    if request.method == "POST":
        parent = ParentUser(
            parent_name=request.form.get("parent_name", "").strip(),
            email=request.form.get("email", "").strip().lower(),
            phone_number=request.form.get("phone_number", "").strip(),
            password_hash="",
        )
        password = request.form.get("password", "").strip()
        if not parent.parent_name or not parent.email or not parent.phone_number or not password:
            flash("Parent name, email, phone number, and password are required.", "error")
        elif ParentUser.query.filter_by(email=parent.email).first():
            flash("A parent with that email already exists.", "error")
        else:
            parent.set_password(password)
            db.session.add(parent)
            db.session.commit()
            create_parent_settings(parent.id)
            log_admin_action("create", "parent_user", entity_name=parent.parent_name, details=parent.email)
            flash("Parent user created successfully.", "success")
            return redirect(url_for("admin.parents"))

    return render_template("admin/parent_form.html", parent=None)


@admin_bp.route("/parents/<int:parent_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_parent(parent_id):
    parent = ParentUser.query.get_or_404(parent_id)
    if request.method == "POST":
        parent.parent_name = request.form.get("parent_name", "").strip()
        parent.email = request.form.get("email", "").strip().lower()
        parent.phone_number = request.form.get("phone_number", "").strip()
        password = request.form.get("password", "").strip()
        if not parent.parent_name or not parent.email or not parent.phone_number:
            flash("Parent name, email, and phone number are required.", "error")
        else:
            if password:
                parent.set_password(password)
            db.session.commit()
            log_admin_action("update", "parent_user", entity_name=parent.parent_name, details=parent.email)
            flash("Parent user updated successfully.", "success")
            return redirect(url_for("admin.parents"))
    return render_template("admin/parent_form.html", parent=parent)


@admin_bp.post("/parents/<int:parent_id>/delete")
@admin_required
def delete_parent(parent_id):
    parent = ParentUser.query.get_or_404(parent_id)
    parent_name = parent.parent_name
    parent_email = parent.email
    db.session.delete(parent)
    db.session.commit()
    log_admin_action("delete", "parent_user", entity_name=parent_name, details=parent_email)
    flash("Parent user deleted successfully.", "success")
    return redirect(url_for("admin.parents"))


@admin_bp.get("/children")
@admin_required
def children():
    search = request.args.get("search", "").strip()
    query = ChildProfile.query.join(ParentUser)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                ChildProfile.child_name.ilike(like),
                ChildProfile.school_name.ilike(like),
                ParentUser.parent_name.ilike(like),
            )
        )
    children_list = query.order_by(ChildProfile.created_at.desc()).all()
    parents_list = ParentUser.query.order_by(ParentUser.parent_name.asc()).all()
    return render_template(
        "admin/children.html",
        children=children_list,
        parents=parents_list,
        search=search,
    )


@admin_bp.route("/children/new", methods=["GET", "POST"])
@admin_required
def create_child():
    parents_list = ParentUser.query.order_by(ParentUser.parent_name.asc()).all()
    if request.method == "POST":
        child_username = request.form.get("child_username", "").strip().lower()
        password = request.form.get("password", "").strip()
        child = ChildProfile(
            parent_id=int(request.form.get("parent_id", "0")),
            child_name=request.form.get("child_name", "").strip(),
            child_username=child_username,
            age=int(request.form.get("age", "0")),
            gender=request.form.get("gender", "").strip(),
            grade=request.form.get("grade", "").strip(),
            school_name=request.form.get("school_name", "").strip(),
            parent_contact=request.form.get("parent_contact", "").strip(),
            device_name=request.form.get("device_name", "").strip(),
            screen_time_limit_hours=float(request.form.get("screen_time_limit_hours", "2.0") or 2.0),
            notes=request.form.get("notes", "").strip(),
        )
        if not child.parent_id or not child.child_name or not child.age or not child.child_username or not password:
            flash("Parent, child name, username, password, and age are required.", "error")
        else:
            child.set_password(password)
            db.session.add(child)
            db.session.commit()
            log_admin_action("create", "child_profile", entity_name=child.child_name, details=child.child_username)
            flash("Child profile created successfully.", "success")
            return redirect(url_for("admin.children"))

    return render_template("admin/child_form.html", child=None, parents=parents_list)


@admin_bp.route("/children/<int:child_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_child(child_id):
    child = ChildProfile.query.get_or_404(child_id)
    parents_list = ParentUser.query.order_by(ParentUser.parent_name.asc()).all()
    if request.method == "POST":
        child.parent_id = int(request.form.get("parent_id", "0"))
        child.child_name = request.form.get("child_name", "").strip()
        child.child_username = request.form.get("child_username", "").strip().lower()
        child.age = int(request.form.get("age", "0"))
        child.gender = request.form.get("gender", "").strip()
        child.grade = request.form.get("grade", "").strip()
        child.school_name = request.form.get("school_name", "").strip()
        child.parent_contact = request.form.get("parent_contact", "").strip()
        child.device_name = request.form.get("device_name", "").strip()
        child.screen_time_limit_hours = float(request.form.get("screen_time_limit_hours", "2.0") or 2.0)
        child.notes = request.form.get("notes", "").strip()
        password = request.form.get("password", "").strip()
        if password:
            child.set_password(password)
        db.session.commit()
        log_admin_action("update", "child_profile", entity_name=child.child_name, details=child.child_username)
        flash("Child profile updated successfully.", "success")
        return redirect(url_for("admin.children"))

    return render_template("admin/child_form.html", child=child, parents=parents_list)


@admin_bp.post("/children/<int:child_id>/delete")
@admin_required
def delete_child(child_id):
    child = ChildProfile.query.get_or_404(child_id)
    child_name = child.child_name
    child_username = child.child_username
    db.session.delete(child)
    db.session.commit()
    log_admin_action("delete", "child_profile", entity_name=child_name, details=child_username)
    flash("Child profile deleted successfully.", "success")
    return redirect(url_for("admin.children"))


@admin_bp.get("/keywords")
@admin_required
def keywords():
    search = request.args.get("search", "").strip()
    query = RestrictedKeyword.query
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                RestrictedKeyword.keyword.ilike(like),
                RestrictedKeyword.category.ilike(like),
            )
        )
    keyword_list = query.order_by(RestrictedKeyword.created_at.desc()).all()
    return render_template("admin/keywords.html", keywords=keyword_list, search=search)


@admin_bp.route("/keywords/new", methods=["GET", "POST"])
@admin_required
def create_keyword():
    if request.method == "POST":
        keyword = RestrictedKeyword(
            keyword=request.form.get("keyword", "").strip().lower(),
            category=request.form.get("category", "").strip(),
            severity=request.form.get("severity", "high").strip().lower(),
            active=request.form.get("active") == "on",
        )
        if not keyword.keyword or not keyword.category:
            flash("Keyword and category are required.", "error")
        elif RestrictedKeyword.query.filter_by(keyword=keyword.keyword).first():
            flash("That keyword already exists.", "error")
        else:
            db.session.add(keyword)
            db.session.commit()
            log_admin_action("create", "restricted_keyword", entity_name=keyword.keyword, details=keyword.category)
            flash("Restricted keyword created successfully.", "success")
            return redirect(url_for("admin.keywords"))
    return render_template("admin/keyword_form.html", keyword=None)


@admin_bp.route("/keywords/<int:keyword_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_keyword(keyword_id):
    keyword = RestrictedKeyword.query.get_or_404(keyword_id)
    if request.method == "POST":
        keyword.keyword = request.form.get("keyword", "").strip().lower()
        keyword.category = request.form.get("category", "").strip()
        keyword.severity = request.form.get("severity", "high").strip().lower()
        keyword.active = request.form.get("active") == "on"
        db.session.commit()
        log_admin_action("update", "restricted_keyword", entity_name=keyword.keyword, details=keyword.category)
        flash("Restricted keyword updated successfully.", "success")
        return redirect(url_for("admin.keywords"))
    return render_template("admin/keyword_form.html", keyword=keyword)


@admin_bp.post("/keywords/<int:keyword_id>/delete")
@admin_required
def delete_keyword(keyword_id):
    keyword = RestrictedKeyword.query.get_or_404(keyword_id)
    keyword_name = keyword.keyword
    keyword_category = keyword.category
    db.session.delete(keyword)
    db.session.commit()
    log_admin_action("delete", "restricted_keyword", entity_name=keyword_name, details=keyword_category)
    flash("Restricted keyword deleted successfully.", "success")
    return redirect(url_for("admin.keywords"))


@admin_bp.get("/alerts")
@admin_required
def alerts():
    severity = request.args.get("severity", "").strip().lower()
    query = Alert.query
    if severity:
        query = query.filter_by(severity=severity)
    alerts_list = query.order_by(Alert.created_at.desc()).all()
    return render_template("admin/alerts.html", alerts=alerts_list, severity=severity)


@admin_bp.get("/ml-monitoring")
@admin_required
def ml_monitoring():
    prediction_rows = MlPredictionLog.query.order_by(MlPredictionLog.created_at.desc()).limit(200).all()
    return render_template("admin/ml_monitoring.html", predictions=prediction_rows)


@admin_bp.get("/history")
@admin_required
def history():
    mode = request.args.get("mode", "").strip().lower()
    query = BrowsingHistory.query
    if mode == "restricted":
        query = query.filter_by(is_restricted=True)
    elif mode == "safe":
        query = query.filter_by(is_restricted=False)
    history_list = query.order_by(BrowsingHistory.created_at.desc()).all()
    safe_count = BrowsingHistory.query.filter_by(is_restricted=False).count()
    restricted_count = BrowsingHistory.query.filter_by(is_restricted=True).count()
    return render_template(
        "admin/history.html",
        history=history_list,
        mode=mode,
        safe_count=safe_count,
        restricted_count=restricted_count,
    )


@admin_bp.get("/reports")
@admin_required
def reports():
    report_rows = Report.query.order_by(Report.created_at.desc()).all()
    monthly_labels = []
    monthly_scores = []
    restricted_counts = []
    average_risk_scores = []
    for report in reversed(report_rows[-6:]):
        monthly_labels.append(report.month_label or report.week_label or f"Report {report.id}")
        monthly_scores.append(report.safe_browsing_score or 0)
        restricted_counts.append(report.restricted_attempts_count or 0)
        average_risk_scores.append((report.summary_json or {}).get("ai_summary", {}).get("average_risk_score", 0))
    return render_template(
        "admin/reports.html",
        reports=report_rows,
        monthly_labels=json.dumps(monthly_labels),
        monthly_scores=json.dumps(monthly_scores),
        restricted_counts=json.dumps(restricted_counts),
        average_risk_scores=json.dumps(average_risk_scores),
    )


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    settings_obj = get_admin_panel_settings()
    if request.method == "POST":
        settings_obj.theme = request.form.get("theme", "pastel-blue").strip()
        settings_obj.security_mode = request.form.get("security_mode", "strict").strip()
        settings_obj.support_email = request.form.get("support_email", "").strip()
        settings_obj.app_info = request.form.get("app_info", "").strip()
        settings_obj.monitoring_enabled = request.form.get("monitoring_enabled") == "on"
        db.session.commit()
        log_admin_action("update", "admin_settings", entity_name=settings_obj.app_info, details=settings_obj.theme)
        flash("Admin settings updated successfully.", "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", settings=settings_obj)


@admin_bp.app_context_processor
def inject_admin_globals():
    return {
        "admin_username": session.get("admin_username"),
        "admin_theme": get_admin_panel_settings().theme if db.session else "pastel-blue",
        "current_year": datetime.utcnow().year,
    }
