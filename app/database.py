import os
from urllib.parse import parse_qs, unquote, urlparse

from peewee import DatabaseProxy, Model
from playhouse.pool import PooledPostgresqlDatabase

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def sync_primary_key_sequence(model) -> None:
    table_name = quote_identifier(model._meta.table_name)
    primary_key = model._meta.primary_key.column_name
    quoted_primary_key = quote_identifier(primary_key)
    db.execute_sql(
        f"""
        SELECT setval(
            pg_get_serial_sequence('{table_name}', '{primary_key}'),
            COALESCE((SELECT MAX({quoted_primary_key}) FROM {table_name}), 1),
            COALESCE((SELECT MAX({quoted_primary_key}) FROM {table_name}) IS NOT NULL, FALSE)
        )
        """
    )


def is_postgres_url(database_url: str) -> bool:
    scheme = urlparse(database_url).scheme.lower()
    return scheme in {"postgres", "postgresql"}


def pooled_connection_settings() -> tuple[int, int]:
    max_connections = int(os.environ.get("DATABASE_POOL_MAX_CONNECTIONS", "1"))
    stale_timeout = int(os.environ.get("DATABASE_POOL_STALE_TIMEOUT", "300"))
    return max_connections, stale_timeout


def build_pooled_database_from_url(database_url: str) -> PooledPostgresqlDatabase:
    parsed = urlparse(database_url)
    database_name = parsed.path.lstrip("/")
    if not database_name:
        raise RuntimeError("DATABASE_URL must include a PostgreSQL database name.")

    connect_kwargs = {
        key: values[-1]
        for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
    }
    max_connections, stale_timeout = pooled_connection_settings()

    return PooledPostgresqlDatabase(
        database_name,
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        max_connections=max_connections,
        stale_timeout=stale_timeout,
        **connect_kwargs,
    )


def init_db(app):
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if not is_postgres_url(database_url):
            raise RuntimeError("DATABASE_URL must use a PostgreSQL connection string.")
        database = build_pooled_database_from_url(database_url)
    elif os.environ.get("DATABASE_HOST") or os.environ.get("DATABASE_NAME"):
        max_connections, stale_timeout = pooled_connection_settings()
        database = PooledPostgresqlDatabase(
            os.environ.get("DATABASE_NAME", "hackathon_db"),
            host=os.environ.get("DATABASE_HOST", "localhost"),
            port=int(os.environ.get("DATABASE_PORT", 5432)),
            user=os.environ.get("DATABASE_USER", "postgres"),
            password=os.environ.get("DATABASE_PASSWORD", "postgres"),
            max_connections=max_connections,
            stale_timeout=stale_timeout,
        )
    else:
        raise RuntimeError(
            "PostgreSQL configuration is required. Set DATABASE_URL or the "
            "DATABASE_HOST, DATABASE_NAME, DATABASE_PORT, DATABASE_USER, and "
            "DATABASE_PASSWORD variables."
        )
    db.initialize(database)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()


def create_tables():
    from app.models import Event, Link, User

    db.connect(reuse_if_open=True)
    try:
        db.create_tables([User, Link, Event], safe=True)
    finally:
        if not db.is_closed():
            db.close()
