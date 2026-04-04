import csv
from datetime import UTC, datetime

from app.models import Event, Link, User
from app.services import import_events_csv, import_urls_csv, import_users_csv


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


def write_events_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "url_id", "user_id", "event_type", "timestamp", "details"],
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


def test_import_users_csv_syncs_primary_key_sequence(app, tmp_path):
    csv_path = tmp_path / "users.csv"
    write_users_csv(
        csv_path,
        [
            {
                "id": "4",
                "username": "seeded-user",
                "email": "seeded-user@example.com",
                "created_at": "2024-04-12 11:11:33",
            }
        ],
    )

    import_users_csv(csv_path)

    user = User.create(username="next-user", email="next-user@example.com")

    assert user.id == 5


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
    link = Link.get(Link.slug == "rP4Z9h")
    assert link.source_id == 1
    assert link.user_id == 9
    assert link.title == "Status board journey"
    assert link.is_active is True


def test_import_urls_csv_updates_existing_links(app, tmp_path):
    Link.create(
        source_id=10,
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


def test_import_urls_csv_updates_links_by_source_id(app, tmp_path):
    Link.create(
        source_id=42,
        slug="older-slug",
        user_id=3,
        target_url="https://old.dev/item",
        title="Old title",
    )

    csv_path = tmp_path / "urls.csv"
    write_urls_csv(
        csv_path,
        [
            {
                "id": "42",
                "user_id": "7",
                "short_code": "new-slug",
                "original_url": "https://seeded.app/new/item",
                "title": "Fresh title",
                "is_active": "True",
                "created_at": "2025-11-02 14:13:50",
                "updated_at": "2026-02-14 03:17:42",
            }
        ],
    )

    summary = import_urls_csv(csv_path)

    assert summary == {"created": 0, "updated": 1, "total": 1}
    link = Link.get(Link.source_id == 42)
    assert link.slug == "new-slug"
    assert link.user_id == 7
    assert link.target_url == "https://seeded.app/new/item"


def test_import_events_csv_creates_events(app, tmp_path):
    User.create(id=1, username="navyjourney21", email="navyjourney21@seeded.app")
    Link.create(
        source_id=1,
        slug="rp4z9h",
        user_id=1,
        target_url="https://seeded.app/opal/journey/1",
    )

    csv_path = tmp_path / "events.csv"
    write_events_csv(
        csv_path,
        [
            {
                "id": "1",
                "url_id": "1",
                "user_id": "1",
                "event_type": "created",
                "timestamp": "2025-11-02 14:13:50",
                "details": '{"short_code":"rP4Z9h","original_url":"https://seeded.app/opal/journey/1"}',
            }
        ],
    )

    summary = import_events_csv(csv_path)

    assert summary == {"created": 1, "updated": 0, "total": 1}
    event = Event.get(Event.source_id == 1)
    assert event.link.source_id == 1
    assert event.user_id == 1
    assert event.event_type == "created"


def test_import_events_csv_updates_existing_events(app, tmp_path):
    User.create(id=7, username="seeder", email="seeder@seeded.app")
    link = Link.create(
        source_id=42,
        slug="link-42",
        user_id=7,
        target_url="https://seeded.app/link/42",
    )
    Event.create(
        source_id=5,
        link=link,
        user_id=7,
        event_type="created",
        details='{"short_code":"link-42"}',
    )

    csv_path = tmp_path / "events.csv"
    write_events_csv(
        csv_path,
        [
            {
                "id": "5",
                "url_id": "42",
                "user_id": "7",
                "event_type": "resolved",
                "timestamp": "2026-01-19 04:11:00",
                "details": '{"short_code":"link-42","visit_count":1}',
            }
        ],
    )

    summary = import_events_csv(csv_path)

    assert summary == {"created": 0, "updated": 1, "total": 1}
    event = Event.get(Event.source_id == 5)
    assert event.link.source_id == 42
    assert event.event_type == "resolved"
    assert event.details == '{"short_code":"link-42","visit_count":1}'


def test_import_events_csv_rejects_unknown_links(app, tmp_path):
    User.create(id=1, username="navyjourney21", email="navyjourney21@seeded.app")

    csv_path = tmp_path / "events.csv"
    write_events_csv(
        csv_path,
        [
            {
                "id": "1",
                "url_id": "999",
                "user_id": "1",
                "event_type": "created",
                "timestamp": "2025-11-02 14:13:50",
                "details": '{"short_code":"missing"}',
            }
        ],
    )

    try:
        import_events_csv(csv_path)
    except ValueError as exc:
        assert str(exc) == "Seed event references an unknown url_id: 999"
    else:
        raise AssertionError("Expected import_events_csv to reject unknown links.")

