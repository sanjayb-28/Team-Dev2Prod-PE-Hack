import os
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.database import db


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch):
    database_url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "TEST_DATABASE_URL or DATABASE_URL must point to a PostgreSQL database."
        )

    monkeypatch.setenv("DATABASE_URL", database_url)

    app = create_app()
    app.config.update(TESTING=True)

    db.connect(reuse_if_open=True)
    db.execute_sql('TRUNCATE TABLE event, link, "user" RESTART IDENTITY CASCADE')
    db.close()

    yield app

    if not db.is_closed():
        db.close()


@pytest.fixture()
def client(app):
    with app.test_client() as test_client:
        yield test_client
