import json
from datetime import UTC, datetime

from app import cache as cache_module
from app.routes import urls as urls_module
from app.database import db
from app.models import Event, Link, User


def create_user(user_id):
    return User.create(
        id=user_id,
        username=f"url-user-{user_id}",
        email=f"url-user-{user_id}@dev2prod.test",
    )


def create_link(user_id, slug="ALQRog", title="Service guide lagoon"):
    return Link.create(
        slug=slug,
        user_id=user_id,
        target_url="https://opswise.net/harbor/journey/1",
        title=title,
        is_active=True,
        created_at=datetime(2025, 6, 4, 0, 7, 0, tzinfo=UTC),
        updated_at=datetime(2025, 11, 19, 3, 17, 29, tzinfo=UTC),
    )


class FakeCacheClient:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, ttl_seconds, value):
        self.values[key] = value

    def scan_iter(self, match):
        prefix = match.rstrip("*")
        return [key for key in self.values if key.startswith(prefix)]

    def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)


def test_create_url(client):
    create_user(1)

    response = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/test",
            "title": "Test URL",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["id"] == 1
    assert payload["user_id"] == 1
    assert payload["original_url"] == "https://example.com/test"
    assert payload["title"] == "Test URL"
    assert payload["is_active"] is True
    assert payload["visit_count"] == 0
    assert len(payload["short_code"]) == 6


def test_create_url_recovers_when_id_sequence_is_behind(client):
    create_user(1)
    create_link(1, slug="seed01")
    create_link(1, slug="seed02")
    db.execute_sql(
        """
        SELECT setval(
            pg_get_serial_sequence('link', 'id'),
            1,
            TRUE
        )
        """
    )

    response = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/test-sequence",
            "title": "Sequence recovery",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["id"] == 3
    assert payload["user_id"] == 1
    assert payload["original_url"] == "https://example.com/test-sequence"


def test_create_url_rejects_missing_user(client):
    response = client.post(
        "/urls",
        json={
            "user_id": 77,
            "original_url": "https://example.com/test",
            "title": "Test URL",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_failed"


def test_create_url_rejects_invalid_original_url(client):
    create_user(1)

    response = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://",
            "title": "Broken URL",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_failed"


def test_create_url_rejects_boolean_user_id(client):
    response = client.post(
        "/urls",
        json={
            "user_id": True,
            "original_url": "https://example.com/test",
            "title": "Test URL",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "User ID must be a positive number."


def test_create_url_rejects_unknown_fields(client):
    create_user(1)

    response = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/test",
            "title": "Test URL",
            "extra": "value",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["details"] == {"fields": ["extra"]}


def test_create_url_rejects_null_short_code_when_field_is_present(client):
    create_user(1)

    response = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/test",
            "title": "Test URL",
            "short_code": None,
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "short_code must be plain text."


def test_list_urls(client):
    create_user(1)
    create_link(1)

    response = client.get("/urls")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "id": 1,
            "user_id": 1,
            "short_code": "ALQRog",
            "original_url": "https://opswise.net/harbor/journey/1",
            "title": "Service guide lagoon",
            "is_active": True,
            "visit_count": 0,
            "created_at": "2025-06-04T00:07:00",
            "updated_at": "2025-11-19T03:17:29",
        }
    ]


def test_list_urls_reports_cache_miss_then_hit(client, monkeypatch):
    create_user(1)
    create_link(1)
    fake_cache = FakeCacheClient()
    monkeypatch.setattr(cache_module, "_cache_client", fake_cache)
    monkeypatch.setattr(cache_module, "_cache_enabled", True)

    first_response = client.get("/urls")
    second_response = client.get("/urls")

    assert first_response.status_code == 200
    assert first_response.headers["X-Cache"] == "MISS"
    assert second_response.status_code == 200
    assert second_response.headers["X-Cache"] == "HIT"


def test_update_url_invalidates_list_cache(client, monkeypatch):
    create_user(1)
    link = create_link(1)
    fake_cache = FakeCacheClient()
    monkeypatch.setattr(cache_module, "_cache_client", fake_cache)
    monkeypatch.setattr(cache_module, "_cache_enabled", True)

    warm_response = client.get("/urls")
    update_response = client.put(f"/urls/{link.id}", json={"title": "Fresh title"})
    refreshed_response = client.get("/urls")

    assert warm_response.headers["X-Cache"] == "MISS"
    assert update_response.status_code == 200
    assert refreshed_response.headers["X-Cache"] == "MISS"


def test_resolve_short_code_invalidates_public_url_cache(client, monkeypatch):
    create_user(1)
    link = create_link(1, slug="cachehit")
    fake_cache = FakeCacheClient()
    monkeypatch.setattr(cache_module, "_cache_client", fake_cache)
    monkeypatch.setattr(cache_module, "_cache_enabled", True)

    warm_list = client.get("/urls")
    warm_detail = client.get(f"/urls/{link.id}")
    resolve_response = client.get("/cachehit", follow_redirects=False)
    refreshed_detail = client.get(f"/urls/{link.id}")

    assert warm_list.headers["X-Cache"] == "MISS"
    assert warm_detail.headers["X-Cache"] == "MISS"
    assert resolve_response.status_code == 302
    assert refreshed_detail.headers["X-Cache"] == "MISS"
    assert refreshed_detail.get_json()["visit_count"] == 1


def test_list_urls_supports_user_filter(client):
    create_user(1)
    create_user(2)
    create_link(1, slug="first01")
    create_link(2, slug="second2")

    response = client.get("/urls?user_id=2")

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    assert response.get_json()[0]["user_id"] == 2


def test_list_urls_rejects_invalid_user_filter(client):
    response = client.get("/urls?user_id=abc")

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "user_id must be a positive number."


def test_list_urls_supports_active_filter(client):
    create_user(1)
    active_link = create_link(1, slug="active1")
    inactive_link = create_link(1, slug="inactive")
    inactive_link.is_active = False
    inactive_link.save()

    response = client.get("/urls?is_active=true")

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    assert response.get_json()[0]["id"] == active_link.id
    assert response.get_json()[0]["is_active"] is True


def test_list_urls_supports_inactive_filter(client):
    create_user(1)
    active_link = create_link(1, slug="active1")
    inactive_link = create_link(1, slug="inactive")
    inactive_link.is_active = False
    inactive_link.save()

    response = client.get("/urls?is_active=false")

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    assert response.get_json()[0]["id"] == inactive_link.id
    assert response.get_json()[0]["is_active"] is False


def test_list_urls_returns_stable_id_order(client):
    create_user(1)
    first_link = Link.create(
        slug="older01",
        user_id=1,
        target_url="https://example.com/older",
        title="Older",
        created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    second_link = Link.create(
        slug="newer01",
        user_id=1,
        target_url="https://example.com/newer",
        title="Newer",
        created_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    response = client.get("/urls")

    assert response.status_code == 200
    assert [row["id"] for row in response.get_json()] == [first_link.id, second_link.id]


def test_get_url_by_id(client):
    create_user(1)
    create_link(1)

    response = client.get("/urls/1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["id"] == 1
    assert payload["short_code"] == "ALQRog"
    assert payload["original_url"] == "https://opswise.net/harbor/journey/1"
    assert payload["visit_count"] == 0


def test_update_url_details(client):
    create_user(1)
    link = create_link(1)

    response = client.put(
        f"/urls/{link.id}",
        json={"title": "Updated Title", "is_active": False},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["id"] == link.id
    assert payload["title"] == "Updated Title"
    assert payload["is_active"] is False
    assert payload["visit_count"] == 0


def test_update_url_rejects_invalid_schema(client):
    create_user(1)
    link = create_link(1)

    response = client.put(f"/urls/{link.id}", json={"title": 123})

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_failed"


def test_update_url_rejects_non_object_body(client):
    create_user(1)
    link = create_link(1)

    response = client.put(
        f"/urls/{link.id}",
        data='"not-an-object"',
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "A JSON body is required."


def test_update_url_advances_updated_at_for_fresh_records(client):
    create_user(1)

    created = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/fresh-update",
            "title": "Fresh update",
        },
    ).get_json()

    response = client.put(
        f"/urls/{created['id']}",
        json={"title": "Updated title"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["updated_at"] > created["updated_at"]


def test_update_url_allows_clearing_title(client):
    create_user(1)
    link = create_link(1, title="Filled title")

    response = client.put(f"/urls/{link.id}", json={"title": None})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["title"] is None
    assert Link.get_by_id(link.id).title is None


def test_update_url_rejects_blank_title(client):
    create_user(1)
    link = create_link(1, title="Filled title")

    response = client.put(f"/urls/{link.id}", json={"title": "   "})

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "Title must be plain text."


def test_create_url_rejects_overlong_short_code(client):
    create_user(1)

    response = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/test",
            "title": "Test URL",
            "short_code": "a" * 33,
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "short_code must be 32 characters or fewer."


def test_create_url_allows_null_title(client):
    create_user(1)

    response = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/test",
            "title": None,
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["user_id"] == 1
    assert payload["original_url"] == "https://example.com/test"
    assert payload["title"] is None


def test_create_url_rejects_blank_title(client):
    create_user(1)

    response = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/test",
            "title": "   ",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "Title must be plain text."


def test_create_url_regenerates_when_generated_short_code_is_taken(client, monkeypatch):
    create_user(1)
    create_link(1, slug="taken1")
    generated_codes = iter(["taken1", "fresh2"])
    monkeypatch.setattr(urls_module, "generate_short_code", lambda length=6: next(generated_codes))

    response = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/fresh",
            "title": "Fresh URL",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["short_code"] == "fresh2"
    assert Link.select().where(Link.slug == "fresh2").exists()


def test_create_url_rejects_requested_short_code_when_it_is_taken(client, monkeypatch):
    create_user(1)
    create_link(1, slug="taken1")

    response = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/fresh-requested",
            "title": "Fresh requested URL",
            "short_code": "taken1",
        },
    )

    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "conflict"
    assert payload["error"]["message"] == "That short code is already in use."
    assert Link.select().count() == 1


def test_create_url_rejects_requested_short_code_when_case_differs_only_by_case(client):
    create_user(1)
    create_link(1, slug="Taken1")

    response = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/fresh-requested",
            "title": "Fresh requested URL",
            "short_code": "taken1",
        },
    )

    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "conflict"
    assert payload["error"]["message"] == "That short code is already in use."
    assert Link.select().count() == 1


def test_delete_url(client):
    create_user(1)
    link = create_link(1, slug="delete-url")
    Event.create(link=link, user_id=1, event_type="created")

    response = client.delete(f"/urls/{link.id}")

    assert response.status_code == 204
    stored_link = Link.get_by_id(link.id)
    assert stored_link.is_active is False
    deleted_event = (
        Event.select()
        .where((Event.link == link) & (Event.event_type == "deleted"))
        .first()
    )
    assert deleted_event is not None
    assert json.loads(deleted_event.details) == {"reason": "user_requested"}


def test_delete_url_is_idempotent(client):
    create_user(1)
    link = create_link(1, slug="delete-twice")

    first_response = client.delete(f"/urls/{link.id}")
    second_response = client.delete(f"/urls/{link.id}")

    assert first_response.status_code == 204
    assert second_response.status_code == 204
    assert (
        Event.select()
        .where((Event.link == link) & (Event.event_type == "deleted"))
        .count()
        == 1
    )


def test_deactivated_public_url_does_not_resolve_or_record_click(client):
    create_user(1)

    created = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/deactivated",
            "title": "Deactivated",
        },
    ).get_json()

    deactivate = client.put(
        f"/urls/{created['id']}",
        json={"is_active": False},
    )
    events_before = client.get("/events").get_json()

    response = client.get(f"/{created['short_code']}", follow_redirects=False)

    assert deactivate.status_code == 200
    assert deactivate.get_json()["is_active"] is False
    assert response.status_code == 404
    assert client.get("/events").get_json() == events_before


def test_resolving_public_short_code_updates_visit_count(client):
    create_user(1)

    created = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/visit-count",
            "title": "Visit count",
        },
    ).get_json()

    response = client.get(f"/{created['short_code']}", follow_redirects=False)

    assert response.status_code == 302
    detail = client.get(f"/urls/{created['id']}").get_json()
    assert detail["visit_count"] == 1


def test_public_short_code_resolution_is_case_insensitive(client):
    create_user(1)

    created = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/mixed-case",
            "title": "Mixed case",
            "short_code": "MiXeD1",
        },
    ).get_json()

    response = client.get("/mixed1", follow_redirects=False)

    assert created["short_code"] == "MiXeD1"
    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com/mixed-case"
    detail = client.get(f"/urls/{created['id']}").get_json()
    assert detail["visit_count"] == 1
