import csv
import os
from dotenv import load_dotenv

load_dotenv()

from peewee import PostgresqlDatabase
from app.database import db
from app.models.user import User
from app.models.url import URL
from app.models.event import Event

database = PostgresqlDatabase(
    os.environ.get("DATABASE_NAME", "hackathon_db"),
    host=os.environ.get("DATABASE_HOST", "localhost"),
    port=int(os.environ.get("DATABASE_PORT", 5432)),
    user=os.environ.get("DATABASE_USER", "postgres"),
    password=os.environ.get("DATABASE_PASSWORD", "postgres"),
)
db.initialize(database)
db.create_tables([User, URL, Event], safe=True)

valid_user_ids = set()
if os.path.exists("users.csv"):
    with open("users.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    data = [{"id": int(r["id"]), "username": r["username"], "email": r["email"], "created_at": r["created_at"]} for r in rows]
    with db.atomic():
        User.insert_many(data).on_conflict_ignore().execute()
    valid_user_ids = {int(r["id"]) for r in rows}
    print(f"Loaded {len(data)} users.")

valid_url_ids = set()
if os.path.exists("urls.csv"):
    with open("urls.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    data = []
    for r in rows:
        uid = int(r["user_id"]) if r.get("user_id") else None
        if uid not in valid_user_ids:
            uid = None
        data.append({
            "id": int(r["id"]),
            "user_id": uid,
            "short_code": r["short_code"],
            "original_url": r["original_url"],
            "title": r.get("title") or None,
            "is_active": r["is_active"].lower() == "true",
            "click_count": 0,
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })
    with db.atomic():
        URL.insert_many(data).on_conflict_ignore().execute()
    valid_url_ids = {int(r["id"]) for r in rows}
    print(f"Loaded {len(data)} URLs.")

if os.path.exists("events.csv"):
    with open("events.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    data = []
    for r in rows:
        uid = int(r["user_id"]) if r.get("user_id") else None
        url_id = int(r["url_id"]) if r.get("url_id") else None
        if uid not in valid_user_ids:
            uid = None
        if url_id not in valid_url_ids:
            url_id = None
        data.append({
            "id": int(r["id"]),
            "url_id": url_id,
            "user_id": uid,
            "event_type": r["event_type"],
            "timestamp": r["timestamp"],
            "details": r.get("details") or None,
        })
    with db.atomic():
        Event.insert_many(data).on_conflict_ignore().execute()
    print(f"Loaded {len(data)} events.")

print("Done!")