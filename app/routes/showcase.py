from datetime import UTC, datetime

from flask import Blueprint, jsonify, render_template, request
from peewee import fn

from app.cache import cache_mode
from app.models import Event, Link, User

showcase_bp = Blueprint("showcase", __name__)


def normalize_prefix(value):
    if not value:
        return ""

    prefix = value.rstrip("/")
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    return prefix


def format_timestamp(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.isoformat(timespec="seconds")
    return value.astimezone(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def build_workload_summary():
    latest_link = Link.select().order_by(Link.updated_at.desc(), Link.id.desc()).first()
    latest_event = Event.select().order_by(Event.timestamp.desc(), Event.id.desc()).first()

    active_urls = (
        Link.select(fn.COUNT(Link.id))
        .where(Link.is_active)
        .scalar()
    )

    return {
        "status": "ok",
        "generated_at": format_timestamp(datetime.now(UTC)),
        "cache_mode": cache_mode(),
        "counts": {
            "users": User.select(fn.COUNT(User.id)).scalar(),
            "urls": Link.select(fn.COUNT(Link.id)).scalar(),
            "active_urls": active_urls,
            "events": Event.select(fn.COUNT(Event.id)).scalar(),
        },
        "latest_link": {
            "slug": latest_link.slug,
            "title": latest_link.title,
            "updated_at": format_timestamp(latest_link.updated_at),
            "is_active": latest_link.is_active,
        }
        if latest_link
        else None,
        "latest_event": {
            "event_type": latest_event.event_type,
            "timestamp": format_timestamp(latest_event.timestamp),
        }
        if latest_event
        else None,
    }


@showcase_bp.get("/")
def workload_home():
    prefix = normalize_prefix(request.headers.get("X-Forwarded-Prefix", ""))
    links = Link.select().order_by(Link.updated_at.desc(), Link.id.desc()).limit(8)
    summary = build_workload_summary()

    return render_template(
        "workload_app.html",
        prefix=prefix,
        links=links,
        summary=summary,
    )


@showcase_bp.get("/status-summary")
def workload_status_summary():
    return jsonify(build_workload_summary())
