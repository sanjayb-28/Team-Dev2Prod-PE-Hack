from datetime import UTC, datetime
from io import BytesIO

from app.models import Event, Link, User
from app.routes import users as users_routes
from peewee import IntegrityError


def create_user(user_id, username, email, created_at=None):
    return User.create(
        id=user_id,
        username=username,
        email=email,
        created_at=created_at or datetime.now(UTC),
    )


def test_bulk_import_users(client):
    csv_payload = "\n".join(
        [
            "id,username,email,created_at",
            "1,silvertrail15,silvertrail15@hackstack.io,2025-09-19 22:25:05",
            "2,urbancanyon36,urbancanyon36@opswise.net,2024-04-09 02:51:03",
        ]
    )

    response = client.post(
        "/users/bulk",
        data={"file": (BytesIO(csv_payload.encode("utf-8")), "users.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.get_json() == {"count": 2}
    assert User.select().count() == 2


def test_list_users(client):
    create_user(
        1,
        "silvertrail15",
        "silvertrail15@hackstack.io",
        created_at=datetime(2025, 9, 19, 22, 25, 5, tzinfo=UTC),
    )
    create_user(
        2,
        "urbancanyon36",
        "urbancanyon36@opswise.net",
        created_at=datetime(2024, 4, 9, 2, 51, 3, tzinfo=UTC),
    )

    response = client.get("/users")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "id": 1,
            "username": "silvertrail15",
            "email": "silvertrail15@hackstack.io",
            "created_at": "2025-09-19T22:25:05",
        },
        {
            "id": 2,
            "username": "urbancanyon36",
            "email": "urbancanyon36@opswise.net",
            "created_at": "2024-04-09T02:51:03",
        },
    ]


def test_get_user_by_id(client):
    create_user(1, "silvertrail15", "silvertrail15@hackstack.io")

    response = client.get("/users/1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["id"] == 1
    assert payload["username"] == "silvertrail15"
    assert payload["email"] == "silvertrail15@hackstack.io"
    assert "created_at" in payload


def test_create_user(client):
    response = client.post(
        "/users",
        json={"username": "testuser", "email": "testuser@example.com"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["id"] == 1
    assert payload["username"] == "testuser"
    assert payload["email"] == "testuser@example.com"
    assert "created_at" in payload


def test_create_user_returns_existing_user_for_exact_duplicate(client):
    create_user(1, "testuser_create", "testuser_create@example.com")

    response = client.post(
        "/users",
        json={
            "username": "testuser_create",
            "email": "testuser_create@example.com",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["id"] == 1
    assert payload["username"] == "testuser_create"
    assert payload["email"] == "testuser_create@example.com"


def test_create_user_reuses_existing_email_with_requested_username(client):
    create_user(1, "old_name", "testuser_create@example.com")

    response = client.post(
        "/users",
        json={
            "username": "testuser_create",
            "email": "testuser_create@example.com",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["id"] == 1
    assert payload["username"] == "testuser_create"
    assert payload["email"] == "testuser_create@example.com"
    assert User.get_by_id(1).username == "testuser_create"


def test_create_user_recovers_from_insert_conflict(client, monkeypatch):
    existing_user = create_user(1, "old_name", "testuser_create@example.com")
    email_checks = iter([None, existing_user])

    def fake_get_existing_user_by_email(email):
        return next(email_checks)

    def fake_create(**kwargs):
        raise IntegrityError()

    monkeypatch.setattr(
        users_routes,
        "get_existing_user_by_email",
        fake_get_existing_user_by_email,
    )
    monkeypatch.setattr(users_routes.User, "create", fake_create)

    response = client.post(
        "/users",
        json={
            "username": "testuser_create",
            "email": "testuser_create@example.com",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["id"] == 1
    assert payload["username"] == "testuser_create"
    assert payload["email"] == "testuser_create@example.com"


def test_create_user_rejects_invalid_schema(client):
    response = client.post(
        "/users",
        json={"username": 123, "email": "testuser@example.com"},
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_failed"


def test_create_user_rejects_unknown_fields(client):
    response = client.post(
        "/users",
        json={
            "username": "testuser",
            "email": "testuser@example.com",
            "role": "admin",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["details"] == {"fields": ["role"]}


def test_create_user_rejects_overlong_username(client):
    response = client.post(
        "/users",
        json={
            "username": "x" * 81,
            "email": "testuser@example.com",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "Username must be 80 characters or fewer."


def test_update_user(client):
    create_user(1, "silvertrail15", "silvertrail15@hackstack.io")

    response = client.put("/users/1", json={"username": "updated_username"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["id"] == 1
    assert payload["username"] == "updated_username"
    assert payload["email"] == "silvertrail15@hackstack.io"


def test_create_user_rejects_duplicate_username(client):
    create_user(1, "sharedname", "first@example.com")

    response = client.post(
        "/users",
        json={"username": "sharedname", "email": "second@example.com"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["message"] == "That username is already in use."


def test_delete_user(client):
    user = create_user(200, "delete-me", "delete-me@example.com")
    link = Link.create(
        slug="delete-user-link",
        user_id=user.id,
        target_url="https://example.com/delete-user",
    )
    Event.create(link=link, user_id=user.id, event_type="created")

    response = client.delete("/users/200")

    assert response.status_code == 204
    assert User.select().where(User.id == 200).count() == 0
    assert Link.get_by_id(link.id).user_id is None
    assert Event.get(Event.link == link).user_id is None


def test_list_users_supports_pagination(client):
    create_user(1, "firstuser", "firstuser@example.com")
    create_user(2, "seconduser", "seconduser@example.com")
    create_user(3, "thirduser", "thirduser@example.com")

    response = client.get("/users?page=2&per_page=1")

    assert response.status_code == 200
    assert response.get_json()["page"] == 2
    assert response.get_json()["per_page"] == 1
    assert response.get_json()["total"] == 3
    assert response.get_json()["users"][0]["id"] == 2


def test_bulk_import_users_rejects_conflicting_email(client):
    create_user(1, "existing", "existing@example.com")
    csv_payload = "\n".join(
        [
            "id,username,email,created_at",
            "2,other,existing@example.com,2025-09-19 22:25:05",
        ]
    )

    response = client.post(
        "/users/bulk",
        data={"file": (BytesIO(csv_payload.encode("utf-8")), "users.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "Seed file contains conflicting user data."
