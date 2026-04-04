from peewee import CharField, BooleanField, DateTimeField, IntegerField
from app.database import BaseModel
import datetime


class URL(BaseModel):
    class Meta:
        table_name = "urls"

    user_id = IntegerField(null=True)
    short_code = CharField(unique=True, max_length=10)
    original_url = CharField()
    title = CharField(null=True)
    is_active = BooleanField(default=True)
    click_count = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)