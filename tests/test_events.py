import json

from app.models import Event, Link, User


def create_user(user_id):
    return User.create(
        id=user_id,
        username=f"user-{user_id}",
        email=f"user-{user_id}@dev2prod.test",
    )


def test_create_link_records_created_event(client):
    create_user(4)

    client.post(
        "/api/links",
        json={
            "slug": "event-created",
            "userId": 4,
            "targetUrl": "https://dev2prod.app/event-created",
        },
    )

    link = Link.get(Link.slug == "event-created")
    event = Event.get(Event.link == link)

    assert event.event_type == "created"
    assert event.user_id == 4
    assert json.loads(event.details) == {
        "original_url": "https://dev2prod.app/event-created",
        "short_code": "event-created",
    }


def test_update_link_records_updated_event(client):
    client.post(
        "/api/links",
        json={
            "slug": "event-updated",
            "targetUrl": "https://dev2prod.app/event-updated",
        },
    )

    client.patch(
        "/api/links/event-updated",
        json={"title": "Updated once"},
    )

    link = Link.get(Link.slug == "event-updated")
    events = list(Event.select().where(Event.link == link).order_by(Event.id))

    assert [event.event_type for event in events] == ["created", "updated"]


def test_resolve_link_records_resolved_event(client):
    client.post(
        "/api/links",
        json={
            "slug": "event-resolved",
            "targetUrl": "https://dev2prod.app/event-resolved",
        },
    )

    client.get("/event-resolved", follow_redirects=False)

    link = Link.get(Link.slug == "event-resolved")
    events = list(Event.select().where(Event.link == link).order_by(Event.id))

    assert [event.event_type for event in events] == ["created", "resolved"]


def test_list_link_events_returns_recent_events_first(client):
    create_user(9)

    client.post(
        "/api/links",
        json={
            "slug": "event-feed",
            "userId": 9,
            "targetUrl": "https://dev2prod.app/event-feed",
        },
    )
    client.patch("/api/links/event-feed", json={"title": "Updated title"})

    response = client.get("/api/links/event-feed/events")

    assert response.status_code == 200
    events = response.get_json()["data"]["events"]
    assert [event["eventType"] for event in events] == ["updated", "created"]
    assert events[0]["details"] == {
        "original_url": "https://dev2prod.app/event-feed",
        "short_code": "event-feed",
    }
    assert events[0]["userId"] == 9


def test_list_link_events_returns_not_found_for_missing_slug(client):
    response = client.get("/api/links/missing-link/events")

    assert response.status_code == 404
    error = response.get_json()["error"]
    assert error["code"] == "not_found"
    assert error["message"] == "We could not find that link."
