from datetime import UTC, datetime
from io import BytesIO

from app.models import User


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


def test_create_user_rejects_invalid_schema(client):
    response = client.post(
        "/users",
        json={"username": 123, "email": "testuser@example.com"},
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_failed"


def test_update_user(client):
    create_user(1, "silvertrail15", "silvertrail15@hackstack.io")

    response = client.put("/users/1", json={"username": "updated_username"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["id"] == 1
    assert payload["username"] == "updated_username"
    assert payload["email"] == "silvertrail15@hackstack.io"


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
