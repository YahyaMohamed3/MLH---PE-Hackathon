import csv
import os

from peewee import DatabaseProxy, Model, PostgresqlDatabase

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


def init_db(app):
    database = PostgresqlDatabase(
        os.environ.get("DATABASE_NAME", "hackathon_db"),
        host=os.environ.get("DATABASE_HOST", "localhost"),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        user=os.environ.get("DATABASE_USER", "postgres"),
        password=os.environ.get("DATABASE_PASSWORD", "postgres"),
    )
    db.initialize(database)

    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()


def _project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _csv_path(filename):
    return os.path.join(_project_root(), filename)


def _to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def seed_from_csv():
    from app.models.event import Event
    from app.models.url import URL
    from app.models.user import User

    users_csv = _csv_path("users.csv")
    urls_csv = _csv_path("urls.csv")
    events_csv = _csv_path("events.csv")

    if os.path.exists(users_csv):
        with open(users_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                rows.append({
                    "id": int(row["id"]),
                    "username": row["username"],
                    "email": row["email"],
                    "created_at": row["created_at"],
                })
            if rows:
                User.insert_many(rows).on_conflict_ignore().execute()

    if os.path.exists(urls_csv):
        with open(urls_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                rows.append({
                    "id": int(row["id"]),
                    "user_id": int(row["user_id"]) if row.get("user_id") else None,
                    "short_code": row["short_code"],
                    "original_url": row["original_url"],
                    "title": row["title"] or None,
                    "is_active": _to_bool(row["is_active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                })
            if rows:
                URL.insert_many(rows).on_conflict_ignore().execute()

    if os.path.exists(events_csv):
        with open(events_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                rows.append({
                    "id": int(row["id"]),
                    "url_id": int(row["url_id"]) if row.get("url_id") else None,
                    "user_id": int(row["user_id"]) if row.get("user_id") else None,
                    "event_type": row["event_type"],
                    "timestamp": row["timestamp"],
                    "details": row["details"],
                })
            if rows:
                Event.insert_many(rows).on_conflict_ignore().execute()


def reset_sequences():
    from app.models.event import Event
    from app.models.url import URL
    from app.models.user import User

    with db.connection_context():
        db.execute_sql(
            f"SELECT setval(pg_get_serial_sequence('{User._meta.table_name}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {User._meta.table_name}), 1), true);"
        )
        db.execute_sql(
            f"SELECT setval(pg_get_serial_sequence('{URL._meta.table_name}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {URL._meta.table_name}), 1), true);"
        )
        db.execute_sql(
            f"SELECT setval(pg_get_serial_sequence('{Event._meta.table_name}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {Event._meta.table_name}), 1), true);"
        )


def create_tables():
    from app.models.event import Event
    from app.models.url import URL
    from app.models.user import User

    with db.connection_context():
        db.create_tables([User, URL, Event], safe=True)
        seed_from_csv()
        reset_sequences()