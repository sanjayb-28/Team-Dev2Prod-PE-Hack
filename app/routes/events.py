import json

from flask import Blueprint, jsonify, request

from app.models import Event

events_bp = Blueprint("events", __name__)


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
        "url_id": event.link.id,
        "user_id": event.user_id,
        "event_type": event.event_type,
        "timestamp": format_timestamp(event.timestamp),
        "details": details,
    }


@events_bp.get("/events")
def list_events():
    events = Event.select().order_by(Event.timestamp.desc(), Event.id.desc())

    url_id = request.args.get("url_id", type=int)
    if url_id is not None:
        events = events.where(Event.link == url_id)

    user_id = request.args.get("user_id", type=int)
    if user_id is not None:
        events = events.where(Event.user_id == user_id)

    event_type = request.args.get("event_type")
    if event_type:
        events = events.where(Event.event_type == event_type.strip())

    return jsonify([serialize_event(event) for event in events])
