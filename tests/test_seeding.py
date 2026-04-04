import csv
from datetime import UTC, datetime

from app.models import Link, User
from app.services import import_urls_csv, import_users_csv


def write_urls_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "user_id",
                "short_code",
                "original_url",
                "title",
                "is_active",
                "created_at",
                "updated_at",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_users_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "username", "email", "created_at"],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_import_users_csv_creates_users(app, tmp_path):
    csv_path = tmp_path / "users.csv"
    write_users_csv(
        csv_path,
        [
            {
                "id": "1",
                "username": "navyjourney21",
                "email": "navyjourney21@seeded.app",
                "created_at": "2024-04-12 11:11:33",
            }
        ],
    )

    summary = import_users_csv(csv_path)

    assert summary == {"created": 1, "updated": 0, "total": 1}
    user = User.get_by_id(1)
    assert user.username == "navyjourney21"
    assert user.email == "navyjourney21@seeded.app"


def test_import_users_csv_updates_existing_users(app, tmp_path):
    User.create(
        id=4,
        username="oldname",
        email="old@example.com",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )

    csv_path = tmp_path / "users.csv"
    write_users_csv(
        csv_path,
        [
            {
                "id": "4",
                "username": "freshname",
                "email": "fresh@example.com",
                "created_at": "2024-04-12 11:11:33",
            }
        ],
    )

    summary = import_users_csv(csv_path)

    assert summary == {"created": 0, "updated": 1, "total": 1}
    user = User.get_by_id(4)
    assert user.username == "freshname"
    assert user.email == "fresh@example.com"


def test_import_users_csv_allows_repeated_usernames(app, tmp_path):
    csv_path = tmp_path / "users.csv"
    write_users_csv(
        csv_path,
        [
            {
                "id": "7",
                "username": "sharedname",
                "email": "shared-one@example.com",
                "created_at": "2024-04-12 11:11:33",
            },
            {
                "id": "8",
                "username": "sharedname",
                "email": "shared-two@example.com",
                "created_at": "2024-04-12 11:11:33",
            },
        ],
    )

    summary = import_users_csv(csv_path)

    assert summary == {"created": 2, "updated": 0, "total": 2}
    assert User.select().where(User.username == "sharedname").count() == 2


def test_import_urls_csv_creates_links(app, tmp_path):
    csv_path = tmp_path / "urls.csv"
    write_urls_csv(
        csv_path,
        [
            {
                "id": "1",
                "user_id": "9",
                "short_code": "rP4Z9h",
                "original_url": "https://seeded.app/opal/journey/1",
                "title": "Status board journey",
                "is_active": "True",
                "created_at": "2025-11-02 14:13:50",
                "updated_at": "2026-02-14 03:17:42",
            }
        ],
    )

    summary = import_urls_csv(csv_path)

    assert summary == {"created": 1, "updated": 0, "total": 1}
    link = Link.get(Link.slug == "rp4z9h")
    assert link.user_id == 9
    assert link.title == "Status board journey"
    assert link.is_active is True


def test_import_urls_csv_updates_existing_links(app, tmp_path):
    Link.create(
        slug="ops123",
        user_id=1,
        target_url="https://old.dev/item",
        title="Old title",
    )

    csv_path = tmp_path / "urls.csv"
    write_urls_csv(
        csv_path,
        [
            {
                "id": "10",
                "user_id": "22",
                "short_code": "ops123",
                "original_url": "https://seeded.app/new/item",
                "title": "Fresh title",
                "is_active": "False",
                "created_at": "2025-11-02 14:13:50",
                "updated_at": "2026-02-14 03:17:42",
            }
        ],
    )

    summary = import_urls_csv(csv_path)

    assert summary == {"created": 0, "updated": 1, "total": 1}
    link = Link.get(Link.slug == "ops123")
    assert link.user_id == 22
    assert link.target_url == "https://seeded.app/new/item"
    assert link.title == "Fresh title"
    assert link.is_active is False
