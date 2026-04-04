from datetime import UTC, datetime

from app.database import db
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


def test_create_event_allows_missing_details(client):
    create_user(1)
    link = create_link(1)

    response = client.post(
        "/events",
        json={
            "url_id": link.id,
            "user_id": 1,
            "event_type": "click",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["url_id"] == link.id
    assert payload["user_id"] == 1
    assert payload["event_type"] == "click"
    assert payload["details"] is None


def test_resolving_short_code_records_click_event_in_events_feed(client):
    create_user(1)

    created = client.post(
        "/urls",
        json={
            "user_id": 1,
            "original_url": "https://example.com/journey",
            "title": "Journey",
        },
    ).get_json()

    response = client.get(f"/{created['short_code']}", follow_redirects=False)

    assert response.status_code == 302

    events = client.get("/events").get_json()
    assert [event["event_type"] for event in events] == ["created", "click"]
    assert events[-1]["details"] == {
        "short_code": created["short_code"],
        "original_url": "https://example.com/journey",
    }


def test_create_event_recovers_when_id_sequence_is_behind(client):
    create_user(1)
    link = create_link(1)
    Event.create(link=link, user_id=1, event_type="created")
    Event.create(link=link, user_id=1, event_type="updated")
    db.execute_sql(
        """
        SELECT setval(
            pg_get_serial_sequence('event', 'id'),
            1,
            TRUE
        )
        """
    )

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
    assert payload["id"] == 3
    assert payload["url_id"] == link.id
    assert payload["user_id"] == 1


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


def test_create_event_requires_user_id(client):
    create_user(1)
    link = create_link(1)

    response = client.post(
        "/events",
        json={
            "url_id": link.id,
            "event_type": "click",
            "details": {"referrer": "https://google.com"},
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "User ID must be a positive number."


def test_create_event_rejects_user_who_does_not_own_url(client):
    create_user(1)
    create_user(2)
    link = create_link(1)

    response = client.post(
        "/events",
        json={
            "url_id": link.id,
            "user_id": 2,
            "event_type": "click",
            "details": {"referrer": "https://google.com"},
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "Choose the user who owns that URL."


def test_create_event_rejects_inactive_url(client):
    create_user(1)
    link = create_link(1)
    link.is_active = False
    link.save()

    response = client.post(
        "/events",
        json={
            "url_id": link.id,
            "user_id": 1,
            "event_type": "click",
            "details": {"referrer": "https://google.com"},
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "Choose an active URL."


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
