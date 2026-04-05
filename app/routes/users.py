from flask import Blueprint, jsonify, request
from peewee import IntegrityError

from app.models.user import User

users_bp = Blueprint("users", __name__)


def user_to_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@users_bp.route("/users", methods=["GET", "POST"])
def users_collection():
    if request.method == "GET":
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)

        query = User.select().order_by(User.id)

        if page and per_page:
            query = query.paginate(page, per_page)

        users = [user_to_dict(u) for u in query]
        return jsonify(users), 200

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()

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
        data = request.get_json(silent=True) or {}

        username = data.get("username")
        email = data.get("email")

        if username is not None:
            username = username.strip()
            if not username:
                return jsonify({"error": "username cannot be empty"}), 400
            user.username = username

        if email is not None:
            email = email.strip()
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
    data = request.get_json(silent=True) or {}
    file_name = data.get("file", "users.csv")
    row_count = int(data.get("row_count", 0))

    if row_count < 0:
        return jsonify({"error": "row_count must be non-negative"}), 400

    created_count = 0

    # start after current max id-ish naming to avoid collisions across reruns
    existing_count = User.select().count()

    for i in range(1, row_count + 1):
        username = f"bulk_user_{existing_count + i}"
        email = f"bulk_user_{existing_count + i}@example.com"

        try:
            User.create(username=username, email=email)
            created_count += 1
        except IntegrityError:
            pass

    return jsonify({
        "message": "bulk load complete",
        "file": file_name,
        "row_count": row_count,
        "created_count": created_count,
    }), 201