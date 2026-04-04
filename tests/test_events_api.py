from datetime import UTC, datetime

from app.models import Event, Link, User


def create_user(user_id):
    return User.create(
        id=user_id,
        username=f"event-user-{user_id}",
        email=f"event-user-{user_id}@dev2prod.test",
    )


def create_link(user_id, slug="ALQRog"):
    return Link.create(
        slug=slug,
        user_id=user_id,
        target_url="https://opswise.net/harbor/journey/1",
        title="Service guide lagoon",
    )


def test_list_events(client):
    create_user(1)
    link = create_link(1)
    Event.create(
        link=link,
        user_id=1,
        event_type="created",
        timestamp=datetime(2025, 6, 4, 0, 7, 0, tzinfo=UTC),
        details='{"short_code":"ALQRog","original_url":"https://opswise.net/harbor/journey/1"}',
    )

    response = client.get("/events")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "id": 1,
            "url_id": link.id,
            "user_id": 1,
            "event_type": "created",
            "timestamp": "2025-06-04T00:07:00",
            "details": {
                "short_code": "ALQRog",
                "original_url": "https://opswise.net/harbor/journey/1",
            },
        }
    ]


def test_list_events_supports_url_filter(client):
    create_user(1)
    link_one = create_link(1, slug="first01")
    link_two = create_link(1, slug="second2")
    Event.create(link=link_one, user_id=1, event_type="created")
    Event.create(link=link_two, user_id=1, event_type="resolved")

    response = client.get(f"/events?url_id={link_two.id}")

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    assert response.get_json()[0]["url_id"] == link_two.id
    assert response.get_json()[0]["event_type"] == "resolved"


def test_list_events_rejects_invalid_url_filter(client):
    response = client.get("/events?url_id=abc")

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "url_id must be a positive number."


def test_list_events_returns_stable_id_order(client):
    create_user(1)
    link = create_link(1)
    first_event = Event.create(
        link=link,
        user_id=1,
        event_type="created",
        timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    second_event = Event.create(
        link=link,
        user_id=1,
        event_type="updated",
        timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    response = client.get("/events")

    assert response.status_code == 200
    assert [row["id"] for row in response.get_json()] == [first_event.id, second_event.id]


def test_create_event(client):
    create_user(1)
    link = create_link(1)

    response = client.post(
        "/events",
        json={
            "url_id": link.id,
            "user_id": 1,
            "event_type": "click",
            "details": {"referrer": "https://google.com"},
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["url_id"] == link.id
    assert payload["user_id"] == 1
    assert payload["event_type"] == "click"
    assert payload["details"] == {"referrer": "https://google.com"}


def test_create_event_rejects_non_object_details(client):
    create_user(1)
    link = create_link(1)

    response = client.post(
        "/events",
        json={
            "url_id": link.id,
            "user_id": 1,
            "event_type": "click",
            "details": ["https://google.com"],
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "details must be a JSON object."


def test_list_events_includes_deleted_url_activity(client):
    create_user(1)
    link = create_link(1, slug="delete-event")
    link.is_active = False
    link.save()
    Event.create(
        link=link,
        user_id=1,
        event_type="deleted",
        details='{"reason":"user_requested"}',
    )

    response = client.get("/events")

    assert response.status_code == 200
    assert response.get_json()[0]["event_type"] == "deleted"
    assert response.get_json()[0]["details"] == {"reason": "user_requested"}
