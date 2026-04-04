import csv

from app.models import Link
from app.services import import_urls_csv


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
