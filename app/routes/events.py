import datetime
import json

from flask import Blueprint, jsonify, request

from app.models.event import Event
from app.models.url import URL
from app.models.user import User

events_bp = Blueprint("events", __name__)


def event_to_dict(event):
    raw_details = event.details
    try:
        details = json.loads(raw_details) if raw_details else {}
    except (TypeError, ValueError):
        details = raw_details

    return {
        "id": event.id,
        "url_id": getattr(event, "url_id", None),
        "user_id": getattr(event, "user_id", None),
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "details": details,
    }


@events_bp.route("/events", methods=["GET", "POST"])
def events_collection():
    if request.method == "GET":
        query = Event.select().order_by(Event.timestamp.desc())

        url_id = request.args.get("url_id", type=int)
        user_id = request.args.get("user_id", type=int)
        event_type = request.args.get("event_type", type=str)

        if url_id is not None:
            query = query.where(Event.url_id == url_id)

        if user_id is not None:
            query = query.where(Event.user_id == user_id)

        if event_type:
            query = query.where(Event.event_type == event_type)

        events = query.limit(100)
        return jsonify([event_to_dict(e) for e in events]), 200

    data = request.get_json(silent=True) or {}

    url_id = data.get("url_id")
    user_id = data.get("user_id")
    event_type = data.get("event_type")
    details = data.get("details", {})

    if url_id is None or not event_type:
        return jsonify({"error": "url_id and event_type are required"}), 400

    try:
        url_id = int(url_id)
    except (TypeError, ValueError):
        return jsonify({"error": "url_id must be an integer"}), 400

    url = URL.get_or_none(URL.id == url_id)
    if not url:
        return jsonify({"error": f"URL {url_id} not found"}), 404

    user = None
    user_id_int = None
    if user_id is not None:
        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError):
            return jsonify({"error": "user_id must be an integer"}), 400

        user = User.get_or_none(User.id == user_id_int)
        if not user:
            return jsonify({"error": f"User {user_id_int} not found"}), 404

    if isinstance(details, (dict, list)):
        details_value = json.dumps(details)
    elif details is None:
        details_value = json.dumps({})
    else:
        details_value = str(details)

    event = Event.create(
        url_id=url_id,
        user_id=user_id_int,
        event_type=event_type,
        timestamp=datetime.datetime.utcnow(),
        details=details_value,
    )

    return jsonify(event_to_dict(event)), 201