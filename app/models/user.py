from datetime import UTC, datetime

from peewee import CharField, DateTimeField

from app.database import BaseModel


class User(BaseModel):
    username = CharField(max_length=80)
    email = CharField(unique=True, max_length=255)
    created_at = DateTimeField(default=lambda: datetime.now(UTC))
