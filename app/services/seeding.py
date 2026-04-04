import csv
from datetime import UTC, datetime
from pathlib import Path

from peewee import IntegrityError

from app.database import db, sync_primary_key_sequence
from app.models import Event, Link, User

CSV_TIMESTAMP = "%Y-%m-%d %H:%M:%S"
REQUIRED_URL_FIELDS = {
    "id",
    "user_id",
    "short_code",
    "original_url",
    "title",
    "is_active",
    "created_at",
    "updated_at",
}
REQUIRED_USER_FIELDS = {
    "id",
    "username",
    "email",
    "created_at",
}
REQUIRED_EVENT_FIELDS = {
    "id",
    "url_id",
    "user_id",
    "event_type",
    "timestamp",
    "details",
}


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, CSV_TIMESTAMP).replace(tzinfo=UTC)


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"Unsupported boolean value: {value}")


def normalize_url_row(row: dict) -> dict:
    return {
        "source_id": int(row["id"]),
        "slug": row["short_code"].strip(),
        "user_id": int(row["user_id"]),
        "target_url": row["original_url"].strip(),
        "title": row["title"].strip() or None,
        "is_active": parse_bool(row["is_active"]),
        "created_at": parse_timestamp(row["created_at"]),
        "updated_at": parse_timestamp(row["updated_at"]),
    }


def normalize_user_row(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "username": row["username"].strip(),
        "email": row["email"].strip().lower(),
        "created_at": parse_timestamp(row["created_at"]),
    }


def normalize_event_row(row: dict) -> dict:
    source_id = int(row["id"])
    link_source_id = int(row["url_id"])
    user_id = int(row["user_id"]) if row["user_id"].strip() else None

    link = Link.select().where(Link.source_id == link_source_id).first()
    if link is None:
        raise ValueError(f"Seed event references an unknown url_id: {link_source_id}")

    if user_id is not None and not User.select().where(User.id == user_id).exists():
        raise ValueError(f"Seed event references an unknown user_id: {user_id}")

    return {
        "source_id": source_id,
        "link": link,
        "user_id": user_id,
        "event_type": row["event_type"].strip(),
        "timestamp": parse_timestamp(row["timestamp"]),
        "details": row["details"].strip() or None,
    }


def import_urls_csv(path: str | Path) -> dict:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not find seed file: {csv_path}")

    opened_here = db.is_closed()
    if opened_here:
        db.connect(reuse_if_open=True)

    created = 0
    updated = 0

    try:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            headers = set(reader.fieldnames or [])
            missing = REQUIRED_URL_FIELDS - headers
            if missing:
                raise ValueError(
                    "Seed file is missing fields: " + ", ".join(sorted(missing))
                )

            for row in reader:
                payload = normalize_url_row(row)
                link = (
                    Link.select()
                    .where(
                        (Link.source_id == payload["source_id"])
                        | (Link.slug == payload["slug"])
                    )
                    .first()
                )
                if link is None:
                    Link.create(**payload)
                    created += 1
                    continue

                for field, value in payload.items():
                    setattr(link, field, value)
                link.save()
                updated += 1
        sync_primary_key_sequence(Link)
    finally:
        if opened_here and not db.is_closed():
            db.close()

    return {
        "created": created,
        "updated": updated,
        "total": created + updated,
    }


def import_users_csv(path: str | Path) -> dict:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not find seed file: {csv_path}")

    opened_here = db.is_closed()
    if opened_here:
        db.connect(reuse_if_open=True)

    created = 0
    updated = 0

    try:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            headers = set(reader.fieldnames or [])
            missing = REQUIRED_USER_FIELDS - headers
            if missing:
                raise ValueError(
                    "Seed file is missing fields: " + ", ".join(sorted(missing))
                )

            for row in reader:
                payload = normalize_user_row(row)
                try:
                    user, was_created = User.get_or_create(
                        id=payload["id"],
                        defaults=payload,
                    )
                    if was_created:
                        created += 1
                        continue

                    for field, value in payload.items():
                        setattr(user, field, value)
                    user.save()
                    updated += 1
                except IntegrityError as error:
                    raise ValueError("Seed file contains conflicting user data.") from error
        sync_primary_key_sequence(User)
    finally:
        if opened_here and not db.is_closed():
            db.close()

    return {
        "created": created,
        "updated": updated,
        "total": created + updated,
    }


def import_events_csv(path: str | Path) -> dict:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not find seed file: {csv_path}")

    opened_here = db.is_closed()
    if opened_here:
        db.connect(reuse_if_open=True)

    created = 0
    updated = 0

    try:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            headers = set(reader.fieldnames or [])
            missing = REQUIRED_EVENT_FIELDS - headers
            if missing:
                raise ValueError(
                    "Seed file is missing fields: " + ", ".join(sorted(missing))
                )

            for row in reader:
                payload = normalize_event_row(row)
                event = Event.select().where(Event.source_id == payload["source_id"]).first()
                if event is None:
                    Event.create(**payload)
                    created += 1
                    continue

                for field, value in payload.items():
                    setattr(event, field, value)
                event.save()
                updated += 1
        sync_primary_key_sequence(Event)
    finally:
        if opened_here and not db.is_closed():
            db.close()

    return {
        "created": created,
        "updated": updated,
        "total": created + updated,
    }
