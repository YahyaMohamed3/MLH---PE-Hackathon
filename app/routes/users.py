from flask import Blueprint, jsonify
from app.models.user import User

users_bp = Blueprint("users", __name__)


@users_bp.route("/users", methods=["GET"])
def list_users():
    users = User.select().order_by(User.created_at.desc()).limit(100)
    return jsonify([{
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "created_at": u.created_at.isoformat(),
    } for u in users])


@users_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    try:
        u = User.get_by_id(user_id)
    except User.DoesNotExist:
        return jsonify({"error": f"User {user_id} not found"}), 404

    return jsonify({
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "created_at": u.created_at.isoformat(),
    })
