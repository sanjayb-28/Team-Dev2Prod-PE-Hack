import pytest

from app.models import Event, Link, User


def create_user(user_id, username=None):
    username = username or f"integration-user-{user_id}"
    return User.create(
        id=user_id,
        username=username,
        email=f"{username}@dev2prod.test",
    )


@pytest.mark.integration
def test_create_link_flow_persists_link_and_event(client):
    create_user(21)

    response = client.post(
        "/api/links",
        json={
            "slug": "integration-create",
            "userId": 21,
            "targetUrl": "https://dev2prod.app/integration-create",
            "title": "Integration create",
        },
    )

    assert response.status_code == 201

    link = Link.get(Link.slug == "integration-create")
    assert link.user_id == 21
    assert link.title == "Integration create"

    created_event = Event.get(
        (Event.link == link) & (Event.event_type == "created")
    )
    assert created_event.user_id == 21


@pytest.mark.integration
def test_update_link_flow_persists_changes_and_event(client):
    create_user(30)
    create_user(31)

    client.post(
        "/api/links",
        json={
            "slug": "integration-update",
            "userId": 30,
            "targetUrl": "https://dev2prod.app/integration-update",
            "title": "Original title",
        },
    )

    response = client.patch(
        "/api/links/integration-update",
        json={
            "userId": 31,
            "title": "Updated title",
            "isActive": False,
        },
    )

    assert response.status_code == 200

    link = Link.get(Link.slug == "integration-update")
    assert link.user_id == 31
    assert link.title == "Updated title"
    assert link.is_active is False

    events = list(Event.select().where(Event.link == link).order_by(Event.id))
    assert [event.event_type for event in events] == ["created", "updated"]
    assert events[-1].user_id == 31


@pytest.mark.integration
def test_resolve_link_flow_increments_visits_and_records_event(client):
    client.post(
        "/api/links",
        json={
            "slug": "integration-resolve",
            "targetUrl": "https://dev2prod.app/integration-resolve",
        },
    )

    response = client.get("/integration-resolve", follow_redirects=False)

    assert response.status_code == 302

    link = Link.get(Link.slug == "integration-resolve")
    assert link.visit_count == 1

    events = list(Event.select().where(Event.link == link).order_by(Event.id))
    assert [event.event_type for event in events] == ["created", "click"]
