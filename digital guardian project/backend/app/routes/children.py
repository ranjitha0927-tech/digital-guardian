from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import ActivityLog, BrowsingHistory, ChildProfile, ParentUser, SafeSearchResult, serialize_child

children_bp = Blueprint("children", __name__)


@children_bp.get("/children")
@jwt_required()
def list_children():
    parent_id = int(get_jwt_identity())
    children = ChildProfile.query.filter_by(parent_id=parent_id).order_by(ChildProfile.created_at.desc()).all()
    return [serialize_child(child) for child in children]


@children_bp.post("/children")
@jwt_required()
def create_child():
    parent_id = int(get_jwt_identity())
    data = request.get_json() or {}
    parent = ParentUser.query.get_or_404(parent_id)
    parent_contact = (data.get("parent_contact") or parent.phone_number or parent.email or "").strip()

    required_fields = [
        "child_name",
        "child_username",
        "password",
        "age",
        "gender",
        "grade",
        "school_name",
        "device_name",
    ]
    missing = [field for field in required_fields if not data.get(field)]
    if not parent_contact:
        missing.append("parent_contact")
    if missing:
        return {"message": f"Missing required fields: {', '.join(missing)}"}, 400

    try:
        child = ChildProfile(
            parent_id=parent_id,
            child_name=data["child_name"].strip(),
            child_username=data["child_username"].strip().lower(),
            age=int(data["age"]),
            gender=data["gender"].strip(),
            grade=data["grade"].strip(),
            school_name=data["school_name"].strip(),
            parent_contact=parent_contact,
            device_name=data["device_name"].strip(),
            screen_time_limit_hours=float(data.get("screen_time_limit_hours") or 2.0),
            notes=(data.get("notes") or "").strip(),
        )
        child.set_password(data["password"].strip())
        db.session.add(child)
        db.session.commit()

        # Seed a small starter trail so new child profiles do not land on empty monitoring screens.
        if not BrowsingHistory.query.filter_by(parent_id=parent_id).first():
            history = BrowsingHistory(
                parent_id=parent_id,
                child_id=child.id,
                search_query="games",
                site_url="https://www.kiddle.co/s.php?q=games",
                device_name=child.device_name,
                activity_type="browser_search",
                matched_keyword=None,
                matched_category=None,
                is_restricted=False,
            )
            activity = ActivityLog(
                parent_id=parent_id,
                child_id=child.id,
                event_type="app_open",
                app_name="YouTube Kids",
                target_name="YouTube Kids",
                target_url="app://YouTube Kids",
                details="Starter activity created for the new child profile.",
                is_restricted=False,
            )
            safe_result = SafeSearchResult(
                parent_id=parent_id,
                child_id=child.id,
                history_id=None,
                search_query="games",
                matched_keyword=None,
                search_topic="games",
                is_restricted=False,
                recommended_sites=[],
                blocked_reason=None,
            )
            db.session.add_all([history, activity, safe_result])
            db.session.commit()
    except ValueError:
        db.session.rollback()
        return {"message": "Age and screen time limit must be numeric values."}, 400
    except IntegrityError:
        db.session.rollback()
        return {"message": "That child username already exists. Please use a unique child username."}, 409
    except Exception as exc:
        db.session.rollback()
        return {"message": f"Unable to create child profile: {exc}"}, 500

    return {"message": "Child profile created.", "child": serialize_child(child)}, 201
