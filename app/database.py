import os
from pathlib import Path

from peewee import DatabaseProxy, Model, PostgresqlDatabase
from playhouse.db_url import connect

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


def init_db(app):
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
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
        database = connect(f"sqlite:///{Path.cwd() / 'local.db'}")
    db.initialize(database)

    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()


def create_tables():
    from app.models import Link

    db.connect(reuse_if_open=True)
    db.create_tables([Link], safe=True)
