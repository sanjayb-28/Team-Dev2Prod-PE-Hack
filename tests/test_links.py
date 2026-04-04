from app.models import Event, Link, User


def create_user(user_id, username=None):
    username = username or f"user-{user_id}"
    return User.create(
        id=user_id,
        username=username,
        email=f"{username}@dev2prod.test",
    )


def test_create_link(client):
    create_user(14)

    response = client.post(
        "/api/links",
        json={
            "slug": "launch-plan",
            "userId": 14,
            "targetUrl": "https://dev2prod.app/launch",
            "title": "Launch plan",
        },
    )

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["slug"] == "launch-plan"
    assert data["userId"] == 14
    assert data["title"] == "Launch plan"


def test_list_links_returns_created_items(client):
    client.post(
        "/api/links",
        json={
            "slug": "runbook",
            "targetUrl": "https://dev2prod.app/runbook",
        },
    )

    response = client.get("/api/links")

    assert response.status_code == 200
    assert len(response.get_json()["data"]["links"]) == 1


def test_get_link_returns_one_item(client):
    create_user(8)

    client.post(
        "/api/links",
        json={
            "slug": "ops-review",
            "userId": 8,
            "targetUrl": "https://dev2prod.app/review",
            "title": "Ops review",
        },
    )

    response = client.get("/api/links/ops-review")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["slug"] == "ops-review"
    assert data["userId"] == 8
    assert data["title"] == "Ops review"


def test_resolve_link_redirects_and_increments_visits(client):
    client.post(
        "/api/links",
        json={
            "slug": "launch-room",
            "targetUrl": "https://dev2prod.app/launch-room",
        },
    )

    response = client.get("/launch-room", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "https://dev2prod.app/launch-room"

    detail_response = client.get("/api/links/launch-room")
    assert detail_response.get_json()["data"]["visitCount"] == 1


def test_resolve_link_rejects_inactive_links(client):
    client.post(
        "/api/links",
        json={
            "slug": "quiet-room",
            "targetUrl": "https://dev2prod.app/quiet-room",
        },
    )
    client.patch("/api/links/quiet-room", json={"isActive": False})

    response = client.get("/quiet-room", follow_redirects=False)

    assert response.status_code == 410
    error = response.get_json()["error"]
    assert error["code"] == "inactive_link"
    assert error["message"] == "This link is inactive."


def test_resolve_link_does_not_record_activity_for_inactive_links(client):
    client.post(
        "/api/links",
        json={
            "slug": "sleeping-guide",
            "targetUrl": "https://dev2prod.app/sleeping-guide",
        },
    )
    client.patch("/api/links/sleeping-guide", json={"isActive": False})
    link = Link.get(Link.slug == "sleeping-guide")
    initial_event_count = Event.select().where(Event.link == link).count()
    initial_visit_count = link.visit_count

    response = client.get("/sleeping-guide", follow_redirects=False)

    assert response.status_code == 410
    link = Link.get(Link.slug == "sleeping-guide")
    assert link.visit_count == initial_visit_count
    assert Event.select().where(Event.link == link).count() == initial_event_count


def test_resolve_link_returns_not_found_for_missing_slug(client):
    response = client.get("/missing-room", follow_redirects=False)

    assert response.status_code == 404
    error = response.get_json()["error"]
    assert error["code"] == "not_found"
    assert error["message"] == "We could not find that link."


def test_update_link_changes_editable_fields(client):
    create_user(5)

    client.post(
        "/api/links",
        json={
            "slug": "status-room",
            "userId": 5,
            "targetUrl": "https://dev2prod.app/status",
            "title": "Status room",
        },
    )

    response = client.patch(
        "/api/links/status-room",
        json={
            "targetUrl": "https://dev2prod.app/live-status",
            "title": "Live status room",
            "isActive": False,
        },
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["targetUrl"] == "https://dev2prod.app/live-status"
    assert data["title"] == "Live status room"
    assert data["isActive"] is False


def test_update_link_rejects_empty_payload(client):
    client.post(
        "/api/links",
        json={
            "slug": "empty-update",
            "targetUrl": "https://dev2prod.app/empty",
        },
    )

    response = client.patch("/api/links/empty-update", json={})

    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "Include at least one field to update."


def test_update_link_rejects_invalid_active_state(client):
    client.post(
        "/api/links",
        json={
            "slug": "bad-active",
            "targetUrl": "https://dev2prod.app/active",
        },
    )

    response = client.patch(
        "/api/links/bad-active",
        json={"isActive": "yes"},
    )

    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "Active status must be true or false."


def test_update_link_rejects_unknown_fields(client):
    client.post(
        "/api/links",
        json={
            "slug": "bad-field",
            "targetUrl": "https://dev2prod.app/field",
        },
    )

    response = client.patch(
        "/api/links/bad-field",
        json={"description": "Not supported yet"},
    )

    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "Only targetUrl, userId, title, and isActive can be updated."
    assert error["details"] == {"fields": ["description"]}


def test_update_link_returns_not_found_for_missing_slug(client):
    response = client.patch(
        "/api/links/missing-link",
        json={"title": "Missing"},
    )

    assert response.status_code == 404
    error = response.get_json()["error"]
    assert error["code"] == "not_found"
    assert error["message"] == "We could not find that link."


def test_create_link_rejects_invalid_urls(client):
    response = client.post(
        "/api/links",
        json={
            "slug": "bad-link",
            "targetUrl": "file://not-allowed",
        },
    )

    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "Use a full http or https URL."


def test_create_link_rejects_invalid_user_id(client):
    response = client.post(
        "/api/links",
        json={
            "slug": "bad-user",
            "userId": 0,
            "targetUrl": "https://dev2prod.app/invalid",
        },
    )

    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "User ID must be a positive number."


def test_create_link_rejects_missing_user(client):
    response = client.post(
        "/api/links",
        json={
            "slug": "unknown-user",
            "userId": 88,
            "targetUrl": "https://dev2prod.app/unknown-user",
        },
    )

    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "Choose an existing user."


def test_update_link_rejects_missing_user(client):
    client.post(
        "/api/links",
        json={
            "slug": "missing-user-update",
            "targetUrl": "https://dev2prod.app/missing-user-update",
        },
    )

    response = client.patch(
        "/api/links/missing-user-update",
        json={"userId": 77},
    )

    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "Choose an existing user."
