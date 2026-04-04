from app.database import db


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_health_endpoint_does_not_open_database_connection(client, monkeypatch):
    def fail_connect(*args, **kwargs):
        raise AssertionError("Health checks should not open a database connection.")

    monkeypatch.setattr(db.obj, "connect", fail_connect)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
