import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    database_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    app = create_app()
    app.config.update(TESTING=True)

    yield app


@pytest.fixture()
def client(app):
    with app.test_client() as test_client:
        yield test_client
