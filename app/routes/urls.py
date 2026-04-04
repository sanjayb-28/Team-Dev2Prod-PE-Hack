from datetime import UTC, datetime
from secrets import choice
from string import ascii_letters, digits
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request
from peewee import DoesNotExist, IntegrityError

from app.errors import error_response
from app.models import Link, User
from app.services import record_event

urls_bp = Blueprint("urls", __name__)
EDITABLE_FIELDS = {"user_id", "original_url", "title", "is_active"}
CREATE_FIELDS = {"user_id", "original_url", "title", "short_code"}
SHORT_CODE_ALPHABET = ascii_letters + digits
SHORT_CODE_MAX_LENGTH = 32
TITLE_MAX_LENGTH = 160


def format_timestamp(value):
    return value.replace(tzinfo=None).isoformat(timespec="seconds")


def serialize_url(link):
    return {
        "id": link.id,
        "user_id": link.user_id,
        "short_code": link.slug,
        "original_url": link.target_url,
        "title": link.title,
        "is_active": link.is_active,
        "created_at": format_timestamp(link.created_at),
        "updated_at": format_timestamp(link.updated_at),
    }


def validate_original_url(original_url):
    if not isinstance(original_url, str) or not original_url.strip():
        return "An original_url value is required."

    value = original_url.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "Use a full http or https URL."

    return None


def validate_user_id(user_id):
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        return "User ID must be a positive number."
    return None


def validate_user_reference(user_id):
    if User.select().where(User.id == user_id).exists():
        return None
    return "Choose an existing user."


def validate_title(title):
    if title is not None and (not isinstance(title, str) or not title.strip()):
        return "Title must be plain text."
    if title is not None and len(title.strip()) > TITLE_MAX_LENGTH:
        return f"Title must be {TITLE_MAX_LENGTH} characters or fewer."
    return None


def parse_bool_query(value):
    if value is None:
        return None

    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError("is_active must be true or false.")


def parse_positive_int_query(value, field_name):
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        raise ValueError(f"{field_name} must be a positive number.")
    if not candidate.isdigit():
        raise ValueError(f"{field_name} must be a positive number.")
    parsed = int(candidate)
    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive number.")
    return parsed


def validate_short_code(short_code):
    if not isinstance(short_code, str) or not short_code.strip():
        return "short_code must be plain text."

    candidate = short_code.strip()
    if len(candidate) > SHORT_CODE_MAX_LENGTH:
        return f"short_code must be {SHORT_CODE_MAX_LENGTH} characters or fewer."
    if not all(character in SHORT_CODE_ALPHABET for character in candidate):
        return "short_code may only contain letters and numbers."

    return None


def get_url_or_none(url_id):
    try:
        return Link.get_by_id(url_id)
    except DoesNotExist:
        return None


def generate_short_code(length=6):
    for _ in range(20):
        candidate = "".join(choice(SHORT_CODE_ALPHABET) for _ in range(length))
        if not Link.select().where(Link.slug == candidate).exists():
            return candidate
    raise RuntimeError("Could not generate a unique short code.")


@urls_bp.get("/urls")
def list_urls():
    urls = Link.select().order_by(Link.id)

    raw_user_id = request.args.get("user_id")
    if raw_user_id is not None:
        try:
            user_id = parse_positive_int_query(raw_user_id, "user_id")
        except ValueError as error:
            return error_response("validation_failed", str(error), 422)
        urls = urls.where(Link.user_id == user_id)

    is_active = request.args.get("is_active")
    if is_active is not None:
        try:
            urls = urls.where(Link.is_active == parse_bool_query(is_active))
        except ValueError as error:
            return error_response("validation_failed", str(error), 422)

    return jsonify([serialize_url(link) for link in urls])


@urls_bp.get("/urls/<int:url_id>")
def get_url(url_id):
    link = get_url_or_none(url_id)
    if link is None:
        return error_response("not_found", "We could not find that URL.", 404)

    return jsonify(serialize_url(link))


@urls_bp.post("/urls")
def create_url():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("validation_failed", "A JSON body is required.", 422)

    unknown_fields = set(payload) - CREATE_FIELDS
    if unknown_fields:
        return error_response(
            "validation_failed",
            "Only user_id, original_url, title, and short_code can be provided.",
            422,
            details={"fields": sorted(unknown_fields)},
        )

    user_id_error = validate_user_id(payload.get("user_id"))
    if user_id_error:
        return error_response("validation_failed", user_id_error, 422)

    user_reference_error = validate_user_reference(payload["user_id"])
    if user_reference_error:
        return error_response("validation_failed", user_reference_error, 422)

    url_error = validate_original_url(payload.get("original_url"))
    if url_error:
        return error_response("validation_failed", url_error, 422)

    title_error = validate_title(payload.get("title"))
    if title_error:
        return error_response("validation_failed", title_error, 422)

    short_code = payload.get("short_code")
    if short_code is not None:
        short_code_error = validate_short_code(short_code)
        if short_code_error:
            return error_response("validation_failed", short_code_error, 422)
        short_code = short_code.strip()
    else:
        short_code = generate_short_code()

    try:
        link = Link.create(
            slug=short_code,
            user_id=payload["user_id"],
            target_url=payload["original_url"].strip(),
            title=payload.get("title").strip() if payload.get("title") else None,
        )
    except IntegrityError:
        return error_response("conflict", "That short code is already in use.", 409)

    record_event(
        link,
        "created",
        {
            "short_code": link.slug,
            "original_url": link.target_url,
        },
    )

    return jsonify(serialize_url(link)), 201


@urls_bp.put("/urls/<int:url_id>")
def update_url(url_id):
    link = get_url_or_none(url_id)
    if link is None:
        return error_response("not_found", "We could not find that URL.", 404)

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
            "Only user_id, original_url, title, and is_active can be updated.",
            422,
            details={"fields": sorted(unknown_fields)},
        )

    if "user_id" in payload:
        user_id_error = validate_user_id(payload.get("user_id"))
        if user_id_error:
            return error_response("validation_failed", user_id_error, 422)
        user_reference_error = validate_user_reference(payload["user_id"])
        if user_reference_error:
            return error_response("validation_failed", user_reference_error, 422)
        link.user_id = payload["user_id"]

    if "original_url" in payload:
        url_error = validate_original_url(payload.get("original_url"))
        if url_error:
            return error_response("validation_failed", url_error, 422)
        link.target_url = payload["original_url"].strip()

    if "title" in payload:
        title_error = validate_title(payload.get("title"))
        if title_error:
            return error_response("validation_failed", title_error, 422)
        link.title = payload["title"].strip()

    if "is_active" in payload:
        if not isinstance(payload["is_active"], bool):
            return error_response(
                "validation_failed",
                "is_active must be true or false.",
                422,
            )
        link.is_active = payload["is_active"]

    link.updated_at = datetime.now(UTC)
    link.save()
    record_event(
        link,
        "updated",
        {
            "short_code": link.slug,
            "original_url": link.target_url,
        },
    )

    return jsonify(serialize_url(link))


@urls_bp.delete("/urls/<int:url_id>")
def delete_url(url_id):
    link = get_url_or_none(url_id)
    if link is None:
        return error_response("not_found", "We could not find that URL.", 404)

    if link.is_active:
        link.is_active = False
        link.updated_at = datetime.now(UTC)
        link.save()
        record_event(
            link,
            "deleted",
            {
                "reason": "user_requested",
            },
        )

    return ("", 204)
