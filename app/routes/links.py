from datetime import UTC, datetime
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request
from peewee import DoesNotExist
from peewee import IntegrityError

from app.models import Link

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


def validate_target_url(target_url):
    if not isinstance(target_url, str) or not target_url.strip():
        return "A destination URL is required."
    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "Use a full http or https URL."
    return None


def validate_user_id(user_id):
    if user_id is not None and (not isinstance(user_id, int) or user_id <= 0):
        return "User ID must be a positive number."
    return None


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

    title_error = validate_title(payload.get("title"))
    if title_error:
        return title_error

    return None


def get_link_or_none(slug):
    try:
        return Link.get(Link.slug == slug)
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
        return jsonify(error={"message": "We could not find that link."}), 404

    return jsonify(data=serialize_link(link))


@links_bp.patch("/api/links/<slug>")
def update_link(slug):
    link = get_link_or_none(slug)
    if link is None:
        return jsonify(error={"message": "We could not find that link."}), 404

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        return jsonify(error={"message": "Include at least one field to update."}), 422

    unknown_fields = set(payload) - EDITABLE_FIELDS
    if unknown_fields:
        return (
            jsonify(
                error={
                    "message": "Only targetUrl, userId, title, and isActive can be updated."
                }
            ),
            422,
        )

    if "targetUrl" in payload:
        target_error = validate_target_url(payload.get("targetUrl"))
        if target_error:
            return jsonify(error={"message": target_error}), 422
        link.target_url = payload["targetUrl"].strip()

    if "userId" in payload:
        user_id_error = validate_user_id(payload.get("userId"))
        if user_id_error:
            return jsonify(error={"message": user_id_error}), 422
        link.user_id = payload["userId"]

    if "title" in payload:
        title_error = validate_title(payload.get("title"))
        if title_error:
            return jsonify(error={"message": title_error}), 422
        link.title = payload["title"].strip()

    if "isActive" in payload:
        if not isinstance(payload["isActive"], bool):
            return jsonify(error={"message": "Active status must be true or false."}), 422
        link.is_active = payload["isActive"]

    link.updated_at = datetime.now(UTC)
    link.save()

    return jsonify(data=serialize_link(link))


@links_bp.post("/api/links")
def create_link():
    payload = request.get_json(silent=True)
    error = validate_payload(payload)
    if error:
        return jsonify(error={"message": error}), 422

    try:
        link = Link.create(
            slug=payload["slug"].strip().lower(),
            user_id=payload.get("userId"),
            target_url=payload["targetUrl"].strip(),
            title=payload.get("title"),
        )
    except IntegrityError:
        return jsonify(error={"message": "This slug is already in use."}), 409

    return jsonify(data=serialize_link(link)), 201
