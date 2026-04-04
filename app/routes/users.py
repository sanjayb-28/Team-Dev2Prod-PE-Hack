from pathlib import Path
from tempfile import NamedTemporaryFile

from flask import Blueprint, jsonify, request
from peewee import DoesNotExist, IntegrityError

from app.errors import error_response
from app.models import User
from app.services import import_users_csv

users_bp = Blueprint("users", __name__)
EDITABLE_FIELDS = {"username", "email"}


def format_timestamp(value):
    return value.replace(tzinfo=None).isoformat(timespec="seconds")


def serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": format_timestamp(user.created_at),
    }


def validate_username(username):
    if not isinstance(username, str) or not username.strip():
        return "Username must be plain text."
    return None


def validate_email(email):
    if not isinstance(email, str) or not email.strip():
        return "Email is required."
    candidate = email.strip().lower()
    if "@" not in candidate or "." not in candidate.split("@")[-1]:
        return "Email must be valid."
    return None


def get_user_or_none(user_id):
    try:
        return User.get_by_id(user_id)
    except DoesNotExist:
        return None


@users_bp.get("/users")
def list_users():
    users = User.select().order_by(User.id)

    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", type=int)
    if page and per_page and page > 0 and per_page > 0:
        total = users.count()
        offset = (page - 1) * per_page
        paged_users = users.offset(offset).limit(per_page)
        return jsonify(
            {
                "users": [serialize_user(user) for user in paged_users],
                "page": page,
                "per_page": per_page,
                "total": total,
            }
        )

    return jsonify([serialize_user(user) for user in users])


@users_bp.get("/users/<int:user_id>")
def get_user(user_id):
    user = get_user_or_none(user_id)
    if user is None:
        return error_response("not_found", "We could not find that user.", 404)

    return jsonify(serialize_user(user))


@users_bp.post("/users")
def create_user():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("validation_failed", "A JSON body is required.", 422)

    username_error = validate_username(payload.get("username"))
    if username_error:
        return error_response("validation_failed", username_error, 422)

    email_error = validate_email(payload.get("email"))
    if email_error:
        return error_response("validation_failed", email_error, 422)

    try:
        user = User.create(
            username=payload["username"].strip(),
            email=payload["email"].strip().lower(),
        )
    except IntegrityError:
        return error_response("conflict", "That email is already in use.", 409)

    return jsonify(serialize_user(user)), 201


@users_bp.put("/users/<int:user_id>")
def update_user(user_id):
    user = get_user_or_none(user_id)
    if user is None:
        return error_response("not_found", "We could not find that user.", 404)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        return error_response(
            "validation_failed",
            "Include at least one field to update.",
            422,
        )

    unknown_fields = set(payload) - EDITABLE_FIELDS
    if unknown_fields:
        return error_response(
            "validation_failed",
            "Only username and email can be updated.",
            422,
            details={"fields": sorted(unknown_fields)},
        )

    if "username" in payload:
        username_error = validate_username(payload.get("username"))
        if username_error:
            return error_response("validation_failed", username_error, 422)
        user.username = payload["username"].strip()

    if "email" in payload:
        email_error = validate_email(payload.get("email"))
        if email_error:
            return error_response("validation_failed", email_error, 422)
        user.email = payload["email"].strip().lower()

    try:
        user.save()
    except IntegrityError:
        return error_response("conflict", "That email is already in use.", 409)

    return jsonify(serialize_user(user))


@users_bp.post("/users/bulk")
def bulk_import_users():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return error_response(
            "validation_failed",
            "Upload a CSV file in the file field.",
            422,
        )

    suffix = Path(upload.filename).suffix or ".csv"
    temp_path = None

    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            temp_path = Path(handle.name)
            upload.save(handle)

        summary = import_users_csv(temp_path)
    except (OSError, ValueError) as error:
        return error_response("validation_failed", str(error), 422)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    return jsonify({"count": summary["total"]}), 201
