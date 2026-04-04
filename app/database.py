import os
from urllib.parse import urlparse

from peewee import DatabaseProxy, Model, PostgresqlDatabase
from playhouse.db_url import connect

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


def is_postgres_url(database_url: str) -> bool:
    scheme = urlparse(database_url).scheme.lower()
    return scheme in {"postgres", "postgresql"}


def init_db(app):
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if not is_postgres_url(database_url):
            raise RuntimeError("DATABASE_URL must use a PostgreSQL connection string.")
        database = connect(database_url)
    elif os.environ.get("DATABASE_HOST") or os.environ.get("DATABASE_NAME"):
        database = PostgresqlDatabase(
            os.environ.get("DATABASE_NAME", "hackathon_db"),
            host=os.environ.get("DATABASE_HOST", "localhost"),
            port=int(os.environ.get("DATABASE_PORT", 5432)),
            user=os.environ.get("DATABASE_USER", "postgres"),
            password=os.environ.get("DATABASE_PASSWORD", "postgres"),
        )
    else:
        raise RuntimeError(
            "PostgreSQL configuration is required. Set DATABASE_URL or the "
            "DATABASE_HOST, DATABASE_NAME, DATABASE_PORT, DATABASE_USER, and "
            "DATABASE_PASSWORD variables."
        )
    db.initialize(database)

    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()


def create_tables():
    from app.models import Event, Link, User

    db.connect(reuse_if_open=True)
    db.create_tables([User, Link, Event], safe=True)
