from pathlib import Path
from tempfile import NamedTemporaryFile

from flask import Blueprint, jsonify, request
from peewee import DoesNotExist, IntegrityError
from peewee import fn

from app.database import sync_primary_key_sequence
from app.errors import error_response
from app.models import Event, Link, User
from app.services import import_users_csv

users_bp = Blueprint("users", __name__)
EDITABLE_FIELDS = {"username", "email"}
CREATE_FIELDS = {"username", "email"}
USERNAME_MAX_LENGTH = 80
EMAIL_MAX_LENGTH = 255


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
    if len(username.strip()) > USERNAME_MAX_LENGTH:
        return f"Username must be {USERNAME_MAX_LENGTH} characters or fewer."
    return None


def validate_email(email):
    if not isinstance(email, str) or not email.strip():
        return "Email is required."
    candidate = email.strip().lower()
    if len(candidate) > EMAIL_MAX_LENGTH:
        return f"Email must be {EMAIL_MAX_LENGTH} characters or fewer."
    if "@" not in candidate or "." not in candidate.split("@")[-1]:
        return "Email must be valid."
    return None


def get_existing_user_by_email(email):
    return User.select().where(User.email == email).first()


def get_existing_user_by_username(username, exclude_user_id=None):
    query = User.select().where(fn.LOWER(User.username) == username.casefold())
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    return query.first()


def get_user_or_none(user_id):
    try:
        return User.get_by_id(user_id)
    except DoesNotExist:
        return None


def reuse_user_for_create(normalized_username, normalized_email, existing_user=None):
    if existing_user is None:
        existing_user = get_existing_user_by_email(normalized_email)
    if existing_user is None:
        return error_response("conflict", "That email is already in use.", 409)

    if existing_user.username.strip().casefold() == normalized_username.casefold():
        if existing_user.username != normalized_username:
            existing_user.username = normalized_username
            existing_user.save()
        return jsonify(serialize_user(existing_user)), 201

    username_owner = get_existing_user_by_username(
        normalized_username,
        exclude_user_id=existing_user.id,
    )
    if username_owner is not None:
        return error_response("conflict", "That username is already in use.", 409)

    existing_user.username = normalized_username
    existing_user.save()
    return jsonify(serialize_user(existing_user)), 201


def resolve_create_user_conflict(normalized_username, normalized_email):
    existing_user = get_existing_user_by_email(normalized_email)
    if existing_user is not None:
        return reuse_user_for_create(
            normalized_username,
            normalized_email,
            existing_user=existing_user,
        )

    username_owner = get_existing_user_by_username(normalized_username)
    if username_owner is not None:
        return error_response("conflict", "That username is already in use.", 409)

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

    unknown_fields = set(payload) - CREATE_FIELDS
    if unknown_fields:
        return error_response(
            "validation_failed",
            "Only username and email can be provided.",
            422,
            details={"fields": sorted(unknown_fields)},
        )

    username_error = validate_username(payload.get("username"))
    if username_error:
        return error_response("validation_failed", username_error, 422)

    email_error = validate_email(payload.get("email"))
    if email_error:
        return error_response("validation_failed", email_error, 422)

    normalized_username = payload["username"].strip()
    normalized_email = payload["email"].strip().lower()
    existing_user = get_existing_user_by_email(normalized_email)
    if existing_user is not None:
        return reuse_user_for_create(normalized_username, normalized_email)

    username_owner = get_existing_user_by_username(normalized_username)
    if username_owner is not None:
        return error_response("conflict", "That username is already in use.", 409)

    try:
        user = User.create(
            username=normalized_username,
            email=normalized_email,
        )
    except IntegrityError:
        conflict_response = resolve_create_user_conflict(
            normalized_username,
            normalized_email,
        )
        if conflict_response is not None:
            return conflict_response

        sync_primary_key_sequence(User)

        try:
            user = User.create(
                username=normalized_username,
                email=normalized_email,
            )
        except IntegrityError:
            conflict_response = resolve_create_user_conflict(
                normalized_username,
                normalized_email,
            )
            if conflict_response is not None:
                return conflict_response
            raise

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
        normalized_username = payload["username"].strip()
        username_owner = get_existing_user_by_username(
            normalized_username,
            exclude_user_id=user.id,
        )
        if username_owner is not None:
            return error_response("conflict", "That username is already in use.", 409)
        user.username = normalized_username

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


@users_bp.delete("/users/<int:user_id>")
def delete_user(user_id):
    user = get_user_or_none(user_id)
    if user is None:
        return error_response("not_found", "We could not find that user.", 404)

    Link.update(user_id=None).where(Link.user_id == user.id).execute()
    Event.update(user_id=None).where(Event.user_id == user.id).execute()
    user.delete_instance()

    return ("", 204)


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
    except (IntegrityError, OSError, ValueError) as error:
        return error_response("validation_failed", str(error), 422)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    return jsonify({"count": summary["total"]}), 201
