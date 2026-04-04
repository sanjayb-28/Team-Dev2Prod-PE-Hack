from app.models import Event, Link, User


def create_user(user_id):
    return User.create(
        id=user_id,
        username=f"surface-user-{user_id}",
        email=f"surface-user-{user_id}@dev2prod.test",
    )


def test_workload_surface_renders_recent_links(client):
    create_user(1)
    Link.create(
        slug="proof01",
        user_id=1,
        target_url="https://example.com/proof",
        title="Proof link",
        is_active=True,
    )

    response = client.get("/", headers={"X-Forwarded-Prefix": "/shortener"})

    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Short links running in the live cluster." in body
    assert "/shortener/health" in body
    assert "/shortener/status-summary" in body
    assert "/shortener/proof01" in body
    assert "Proof link" in body
    assert "Live service check" in body
    assert "Dataset footprint" in body


def test_workload_status_summary_reports_live_counts(client):
    create_user(1)
    create_user(2)

    first_link = Link.create(
        slug="alpha01",
        user_id=1,
        target_url="https://example.com/alpha",
        title="Alpha link",
        is_active=True,
    )
    Link.create(
        slug="beta02",
        user_id=2,
        target_url="https://example.com/beta",
        title="Beta link",
        is_active=False,
    )
    Event.create(
        link=first_link,
        user_id=1,
        event_type="clicked",
    )

    response = client.get("/status-summary")

    assert response.status_code == 200

    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["counts"] == {
        "users": 2,
        "urls": 2,
        "active_urls": 1,
        "events": 1,
    }
    assert payload["latest_link"]["slug"] == "beta02"
    assert payload["latest_event"]["event_type"] == "clicked"
