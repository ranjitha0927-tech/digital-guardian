from flask import Blueprint, request
from flask_jwt_extended import create_access_token

from ..extensions import db
from ..models import ChildProfile, ParentUser, create_parent_settings

auth_bp = Blueprint("auth", __name__)


def _ensure_demo_child(parent: ParentUser):
    existing = ChildProfile.query.filter_by(parent_id=parent.id).order_by(ChildProfile.created_at.desc()).first()
    if existing is not None:
        return None

    demo_username = f"child{parent.id}_demo"
    demo_password = f"DG-{parent.id}123"
    child = ChildProfile(
        parent_id=parent.id,
        child_name=f"{parent.parent_name}'s Child",
        child_username=demo_username,
        age=12,
        gender="Prefer not to say",
        grade="Grade 7",
        school_name="Digital Guardian Demo School",
        parent_contact=parent.phone_number or parent.email,
        device_name="Family Tablet",
        screen_time_limit_hours=2.0,
        notes="Auto-generated demo child profile for project walkthroughs.",
    )
    child.set_password(demo_password)
    db.session.add(child)
    db.session.commit()
    return {
        "id": child.id,
        "child_name": child.child_name,
        "child_username": child.child_username,
        "password": demo_password,
    }


@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    parent_name = data.get("parent_name", "").strip()
    email = data.get("email", "").strip().lower()
    phone_number = data.get("phone_number", "").strip()
    password = data.get("password", "").strip()

    if not parent_name or not email or not phone_number or not password:
        return {"message": "Parent name, email, phone number, and password are required."}, 400

    if ParentUser.query.filter_by(email=email).first():
        return {"message": "An account with this email already exists."}, 409

    user = ParentUser(
        parent_name=parent_name,
        email=email,
        phone_number=phone_number,
        password_hash="",
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    create_parent_settings(user.id)
    demo_child = _ensure_demo_child(user)

    token = create_access_token(identity=str(user.id))
    return {
        "message": "Registration successful.",
        "access_token": token,
        "parent": {
            "id": user.id,
            "parent_name": user.parent_name,
            "email": user.email,
            "phone_number": user.phone_number,
        },
        "demo_child": demo_child,
    }, 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    user = ParentUser.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return {"message": "Invalid email or password."}, 401

    demo_child = _ensure_demo_child(user)
    token = create_access_token(identity=str(user.id))
    return {
        "message": "Login successful.",
        "access_token": token,
        "parent": {
            "id": user.id,
            "parent_name": user.parent_name,
            "email": user.email,
            "phone_number": user.phone_number,
        },
        "demo_child": demo_child,
    }


@auth_bp.post("/child/login")
def child_login():
    data = request.get_json() or {}
    username = data.get("child_username", "").strip().lower()
    password = data.get("password", "").strip()

    child = ChildProfile.query.filter_by(child_username=username, is_active=True).first()
    if child is None:
        return {"message": "No child profile found for that username. Create a child profile from the parent dashboard first."}, 404
    if not child.check_password(password):
        return {"message": "Invalid child credentials."}, 401

    token = create_access_token(identity={"role": "child", "child_id": child.id, "parent_id": child.parent_id})
    return {
        "message": "Child login successful.",
        "access_token": token,
        "child": {
            "id": child.id,
            "child_name": child.child_name,
            "parent_id": child.parent_id,
        },
    }
