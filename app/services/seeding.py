import csv
from datetime import UTC, datetime
from pathlib import Path

from app.database import db
from app.models import Link, User

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
        "slug": row["short_code"].strip().lower(),
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
                link, was_created = Link.get_or_create(
                    slug=payload["slug"],
                    defaults=payload,
                )
                if was_created:
                    created += 1
                    continue

                for field, value in payload.items():
                    setattr(link, field, value)
                link.save()
                updated += 1
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
    finally:
        if opened_here and not db.is_closed():
            db.close()

    return {
        "created": created,
        "updated": updated,
        "total": created + updated,
    }
