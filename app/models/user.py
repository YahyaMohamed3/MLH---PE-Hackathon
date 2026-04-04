from peewee import CharField, DateTimeField
from app.database import BaseModel
import datetime


class User(BaseModel):
    class Meta:
        table_name = "users"

    username = CharField(unique=True)
    email = CharField(unique=True)
    created_at = DateTimeField(default=datetime.datetime.now)
