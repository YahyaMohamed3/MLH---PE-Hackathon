from peewee import CharField, DateTimeField, IntegerField, TextField
from app.database import BaseModel
import datetime


class Event(BaseModel):
    class Meta:
        table_name = "events"

    url_id = IntegerField(null=True)
    user_id = IntegerField(null=True)
    event_type = CharField()
    timestamp = DateTimeField(default=datetime.datetime.now)
    details = TextField(null=True)