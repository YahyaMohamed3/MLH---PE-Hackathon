import csv
import os

from flask import Blueprint, jsonify, request
from peewee import IntegrityError

from app.models.user import User
from app.database import db

users_bp = Blueprint("users", __name__)


def user_to_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _csv_path(filename):
    # Use basename to prevent path traversal directory escapes
    safe_filename = os.path.basename(filename)
    return os.path.join(_project_root(), safe_filename)


def _parse_int(value, default=None):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_text(value):
    return str(value or "").strip()


def _load_csv_users(file_name, limit=None):
    path = _csv_path(file_name)
    if not os.path.exists(path):
        return None, f"file '{file_name}' not found"

    rows = []
    seen_pairs = set()

    # utf-8-sig handles potential BOM characters in Windows-saved CSVs
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            username = _normalize_text(row.get("username"))
            email = _normalize_text(row.get("email"))

            if not username or not email:
                continue

            key = (username, email)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)

            rows.append({
                "username": username,
                "email": email,
            })

            if limit is not None and len(rows) >= limit:
                break

    return rows, None


@users_bp.route("/users", methods=["GET", "POST"])
def users_collection():
    if request.method == "GET":
        page = _parse_int(request.args.get("page"), default=None)
        per_page = _parse_int(request.args.get("per_page"), default=None)

        query = User.select().order_by(User.id)

        if page is not None or per_page is not None:
            if page is None or per_page is None:
                return jsonify({"error": "page and per_page must both be provided"}), 400
            if page < 1 or per_page < 1:
                return jsonify({"error": "page and per_page must be positive integers"}), 400
            query = query.paginate(page, per_page)

        return jsonify([user_to_dict(u) for u in query]), 200

    # force=True allows parsing even if test client forgot Content-Type header
    data = request.get_json(silent=True, force=True)
    if data is None:
        data = {}
        
    if not isinstance(data, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    username = _normalize_text(data.get("username"))
    email = _normalize_text(data.get("email"))

    if not username or not email:
        return jsonify({"error": "username and email are required"}), 400

    try:
        user = User.create(username=username, email=email)
        return jsonify(user_to_dict(user)), 201
    except IntegrityError:
        return jsonify({"error": "duplicate user"}), 409


@users_bp.route("/users/<int:user_id>", methods=["GET", "PUT", "DELETE"])
def user_detail(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        return jsonify({"error": f"User {user_id} not found"}), 404

    if request.method == "GET":
        return jsonify(user_to_dict(user)), 200

    if request.method == "PUT":
        data = request.get_json(silent=True, force=True)
        if data is None:
            data = {}
            
        if not isinstance(data, dict):
            return jsonify({"error": "request body must be a JSON object"}), 400

        username = data.get("username")
        email = data.get("email")

        if username is None and email is None:
            return jsonify({"error": "at least one of username or email is required"}), 400

        if username is not None:
            username = _normalize_text(username)
            if not username:
                return jsonify({"error": "username cannot be empty"}), 400
            user.username = username

        if email is not None:
            email = _normalize_text(email)
            if not email:
                return jsonify({"error": "email cannot be empty"}), 400
            user.email = email

        try:
            user.save()
            return jsonify(user_to_dict(user)), 200
        except IntegrityError:
            return jsonify({"error": "duplicate value"}), 409

    user.delete_instance()
    return "", 204


@users_bp.route("/users/bulk", methods=["POST"])
def load_users_bulk():
    data = request.get_json(silent=True, force=True)
    if data is None:
        data = {}
        
    if not isinstance(data, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    file_name = _normalize_text(data.get("file")) or "users.csv"
    row_count = _parse_int(data.get("row_count"), default=None)

    if row_count is not None and row_count < 0:
        return jsonify({"error": "row_count must be non-negative"}), 400

    csv_rows, err = _load_csv_users(file_name, limit=row_count)
    if csv_rows is None:
        return jsonify({"error": err}), 404

    processed_count = len(csv_rows)

    if not csv_rows:
        return jsonify({
            "message": "bulk load complete",
            "file": file_name,
            "row_count": processed_count,
            "imported": 0,
        }), 201

    rows_to_insert = []
    batch_usernames = set()
    batch_emails = set()

    for row in csv_rows:
        username = row["username"]
        email = row["email"]

        # Only check intra-batch duplicates here. Let the DB handle global unique constraints.
        if username in batch_usernames or email in batch_emails:
            continue

        rows_to_insert.append({
            "username": username,
            "email": email,
        })
        batch_usernames.add(username)
        batch_emails.add(email)

    imported_count = 0

    if rows_to_insert:
        before_count = User.select().count()

        with db.atomic():
            for i in range(0, len(rows_to_insert), 100):
                chunk = rows_to_insert[i:i + 100]
                User.insert_many(chunk).on_conflict_ignore().execute()

        after_count = User.select().count()
        imported_count = max(after_count - before_count, 0)

    return jsonify({
        "message": "bulk load complete",
        "file": file_name,
        "row_count": processed_count,
        "imported": imported_count,
    }), 201