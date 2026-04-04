import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from flask import Blueprint, jsonify, redirect, request
from peewee import DoesNotExist
from peewee import IntegrityError
from peewee import fn

from app.cache import URL_CACHE_PREFIX, invalidate_cache_prefix
from app.errors import error_response
from app.models import Event, Link, User
from app.services import record_event

links_bp = Blueprint("links", __name__)
EDITABLE_FIELDS = {"targetUrl", "userId", "title", "isActive"}


def serialize_link(link):
    return {
        "slug": link.slug,
        "userId": link.user_id,
        "targetUrl": link.target_url,
        "title": link.title,
        "isActive": link.is_active,
        "visitCount": link.visit_count,
        "createdAt": link.created_at.isoformat(),
        "updatedAt": link.updated_at.isoformat(),
    }


def serialize_event(event):
    details = event.details
    if details is not None:
        try:
            details = json.loads(details)
        except json.JSONDecodeError:
            pass

    return {
        "id": event.source_id or event.id,
        "userId": event.user_id,
        "eventType": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "details": details,
    }


def next_visible_timestamp(current_value):
    if current_value.tzinfo is None:
        now = datetime.now().replace(microsecond=0)
        current_floor = current_value.replace(microsecond=0)
    else:
        now = datetime.now(UTC)
        current_floor = current_value.astimezone(UTC).replace(microsecond=0)
    now_floor = now.replace(microsecond=0)
    if now_floor <= current_floor:
        return current_floor + timedelta(seconds=1)
    return now


def validate_target_url(target_url):
    if not isinstance(target_url, str) or not target_url.strip():
        return "A destination URL is required."
    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "Use a full http or https URL."
    return None


def validate_user_id(user_id):
    if user_id is not None and (
        isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0
    ):
        return "User ID must be a positive number."
    return None


def validate_user_reference(user_id):
    if user_id is None:
        return None
    if User.select().where(User.id == user_id).exists():
        return None
    return "Choose an existing user."


def validate_title(title):
    if title is not None and (not isinstance(title, str) or not title.strip()):
        return "Title must be plain text."
    return None


def validate_payload(payload):
    if not isinstance(payload, dict):
        return "A JSON body is required."

    slug = payload.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        return "A slug is required."

    target_error = validate_target_url(payload.get("targetUrl"))
    if target_error:
        return target_error

    user_id_error = validate_user_id(payload.get("userId"))
    if user_id_error:
        return user_id_error
    user_reference_error = validate_user_reference(payload.get("userId"))
    if user_reference_error:
        return user_reference_error

    title_error = validate_title(payload.get("title"))
    if title_error:
        return title_error

    return None


def get_link_or_none(slug):
    try:
        return Link.get(fn.LOWER(Link.slug) == slug.lower())
    except DoesNotExist:
        return None


@links_bp.get("/api/links")
def list_links():
    links = Link.select().order_by(Link.created_at.desc())
    return jsonify(data={"links": [serialize_link(link) for link in links]})


@links_bp.get("/api/links/<slug>")
def get_link(slug):
    link = get_link_or_none(slug)
    if link is None:
        return error_response("not_found", "We could not find that link.", 404)

    return jsonify(data=serialize_link(link))


@links_bp.get("/api/links/<slug>/events")
def list_link_events(slug):
    link = get_link_or_none(slug)
    if link is None:
        return error_response("not_found", "We could not find that link.", 404)

    events = (
        Event.select()
        .where(Event.link == link)
        .order_by(Event.timestamp.desc(), Event.id.desc())
    )
    return jsonify(data={"events": [serialize_event(event) for event in events]})


@links_bp.get("/<slug>")
def resolve_link(slug):
    link = get_link_or_none(slug)
    if link is None:
        return error_response("not_found", "We could not find that link.", 404)

    if not link.is_active:
        return error_response("inactive_link", "This link is inactive.", 404)

    link.visit_count += 1
    link.updated_at = next_visible_timestamp(link.updated_at)
    link.save()
    record_event(
        link,
        "click",
        {
            "short_code": link.slug,
            "original_url": link.target_url,
        },
    )
    invalidate_cache_prefix(URL_CACHE_PREFIX)

    return redirect(link.target_url, code=302)


@links_bp.patch("/api/links/<slug>")
def update_link(slug):
    link = get_link_or_none(slug)
    if link is None:
        return error_response("not_found", "We could not find that link.", 404)

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
            "Only targetUrl, userId, title, and isActive can be updated.",
            422,
            details={"fields": sorted(unknown_fields)},
        )

    if "targetUrl" in payload:
        target_error = validate_target_url(payload.get("targetUrl"))
        if target_error:
            return error_response("validation_failed", target_error, 422)
        link.target_url = payload["targetUrl"].strip()

    if "userId" in payload:
        user_id_error = validate_user_id(payload.get("userId"))
        if user_id_error:
            return error_response("validation_failed", user_id_error, 422)
        user_reference_error = validate_user_reference(payload.get("userId"))
        if user_reference_error:
            return error_response("validation_failed", user_reference_error, 422)
        link.user_id = payload["userId"]

    if "title" in payload:
        title_error = validate_title(payload.get("title"))
        if title_error:
            return error_response("validation_failed", title_error, 422)
        link.title = payload["title"].strip()

    if "isActive" in payload:
        if not isinstance(payload["isActive"], bool):
            return error_response(
                "validation_failed",
                "Active status must be true or false.",
                422,
            )
        link.is_active = payload["isActive"]

    link.updated_at = next_visible_timestamp(link.updated_at)
    link.save()
    record_event(
        link,
        "updated",
        {
            "short_code": link.slug,
            "original_url": link.target_url,
        },
    )

    return jsonify(data=serialize_link(link))


@links_bp.post("/api/links")
def create_link():
    payload = request.get_json(silent=True)
    error = validate_payload(payload)
    if error:
        return error_response("validation_failed", error, 422)

    try:
        link = Link.create(
            slug=payload["slug"].strip().lower(),
            user_id=payload.get("userId"),
            target_url=payload["targetUrl"].strip(),
            title=payload.get("title"),
        )
    except IntegrityError:
        return error_response("conflict", "This slug is already in use.", 409)

    record_event(
        link,
        "created",
        {
            "short_code": link.slug,
            "original_url": link.target_url,
        },
    )

    return jsonify(data=serialize_link(link)), 201
