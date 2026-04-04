from app.models import Link, User


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
    assert "/shortener/proof01" in body
    assert "Proof link" in body
