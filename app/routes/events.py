import json

from flask import Blueprint, jsonify, request
from peewee import DoesNotExist

from app.errors import error_response
from app.models import Event, Link, User

events_bp = Blueprint("events", __name__)
CREATE_FIELDS = {"url_id", "user_id", "event_type", "details"}
EVENT_TYPE_MAX_LENGTH = 32


def format_timestamp(value):
    return value.replace(tzinfo=None).isoformat(timespec="seconds")


def serialize_event(event):
    details = event.details
    if details is not None:
        try:
            details = json.loads(details)
        except json.JSONDecodeError:
            pass

    return {
        "id": event.id,
        "url_id": event.link_id,
        "user_id": event.user_id,
        "event_type": event.event_type,
        "timestamp": format_timestamp(event.timestamp),
        "details": details,
    }


def validate_event_type(event_type):
    if not isinstance(event_type, str) or not event_type.strip():
        return "event_type must be plain text."
    if len(event_type.strip()) > EVENT_TYPE_MAX_LENGTH:
        return f"event_type must be {EVENT_TYPE_MAX_LENGTH} characters or fewer."
    return None


def validate_user_id(user_id):
    if user_id is not None and (
        isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0
    ):
        return "User ID must be a positive number."
    return None


def validate_url_id(url_id):
    if isinstance(url_id, bool) or not isinstance(url_id, int) or url_id <= 0:
        return "URL ID must be a positive number."
    return None


def get_link_or_none(url_id):
    try:
        return Link.get_by_id(url_id)
    except DoesNotExist:
        return None


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


@events_bp.get("/events")
def list_events():
    events = Event.select().order_by(Event.id)

    raw_url_id = request.args.get("url_id")
    if raw_url_id is not None:
        try:
            url_id = parse_positive_int_query(raw_url_id, "url_id")
        except ValueError as error:
            return error_response("validation_failed", str(error), 422)
        events = events.where(Event.link == url_id)

    raw_user_id = request.args.get("user_id")
    if raw_user_id is not None:
        try:
            user_id = parse_positive_int_query(raw_user_id, "user_id")
        except ValueError as error:
            return error_response("validation_failed", str(error), 422)
        events = events.where(Event.user_id == user_id)

    event_type = request.args.get("event_type")
    if event_type:
        events = events.where(Event.event_type == event_type.strip())

    return jsonify([serialize_event(event) for event in events])


@events_bp.post("/events")
def create_event():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("validation_failed", "A JSON body is required.", 422)

    unknown_fields = set(payload) - CREATE_FIELDS
    if unknown_fields:
        return error_response(
            "validation_failed",
            "Only url_id, user_id, event_type, and details can be provided.",
            422,
            details={"fields": sorted(unknown_fields)},
        )

    url_id_error = validate_url_id(payload.get("url_id"))
    if url_id_error:
        return error_response("validation_failed", url_id_error, 422)

    user_id_error = validate_user_id(payload.get("user_id"))
    if user_id_error:
        return error_response("validation_failed", user_id_error, 422)

    event_type_error = validate_event_type(payload.get("event_type"))
    if event_type_error:
        return error_response("validation_failed", event_type_error, 422)

    link = get_link_or_none(payload["url_id"])
    if link is None:
        return error_response("not_found", "We could not find that URL.", 404)
    if not link.is_active:
        return error_response("validation_failed", "Choose an active URL.", 422)

    user_id = payload.get("user_id")
    if user_id is not None and not User.select().where(User.id == user_id).exists():
        return error_response("validation_failed", "Choose an existing user.", 422)

    details = payload.get("details")
    if details is not None:
        if not isinstance(details, dict):
            return error_response(
                "validation_failed",
                "details must be a JSON object.",
                422,
            )
        try:
            details = json.dumps(details, sort_keys=True)
        except TypeError:
            return error_response(
                "validation_failed",
                "details must be valid JSON data.",
                422,
            )

    event = Event.create(
        link=link,
        user_id=user_id,
        event_type=payload["event_type"].strip(),
        details=details,
    )

    return jsonify(serialize_event(event)), 201
