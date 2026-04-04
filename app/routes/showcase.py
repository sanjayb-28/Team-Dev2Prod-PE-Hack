from flask import Blueprint, render_template, request

from app.models import Link

showcase_bp = Blueprint("showcase", __name__)


def normalize_prefix(value):
    if not value:
        return ""

    prefix = value.rstrip("/")
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    return prefix


@showcase_bp.get("/")
def workload_home():
    prefix = normalize_prefix(request.headers.get("X-Forwarded-Prefix", ""))
    links = Link.select().order_by(Link.updated_at.desc(), Link.id.desc()).limit(8)

    return render_template(
        "workload_app.html",
        prefix=prefix,
        links=links,
    )
