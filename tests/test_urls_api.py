from datetime import UTC, datetime

from app.models import Link, User


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
    assert len(payload["short_code"]) == 6


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
            "created_at": "2025-06-04T00:07:00",
            "updated_at": "2025-11-19T03:17:29",
        }
    ]


def test_list_urls_supports_user_filter(client):
    create_user(1)
    create_user(2)
    create_link(1, slug="first01")
    create_link(2, slug="second2")

    response = client.get("/urls?user_id=2")

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    assert response.get_json()[0]["user_id"] == 2


def test_get_url_by_id(client):
    create_user(1)
    create_link(1)

    response = client.get("/urls/1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["id"] == 1
    assert payload["short_code"] == "ALQRog"
    assert payload["original_url"] == "https://opswise.net/harbor/journey/1"


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


def test_update_url_rejects_invalid_schema(client):
    create_user(1)
    link = create_link(1)

    response = client.put(f"/urls/{link.id}", json={"title": 123})

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_failed"
