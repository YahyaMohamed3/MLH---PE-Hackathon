import datetime
import json

from flask import Blueprint, jsonify, request
from peewee import IntegrityError

from app.models.event import Event
from app.models.url import URL
from app.models.user import User

events_bp = Blueprint("events", __name__)

ALLOWED_EVENT_TYPES = {"created", "updated", "click", "deleted", "deactivated"}


def parse_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_event_type(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if text == "clicked":
        return "click"
    return text


def parse_details(raw_details):
    try:
        return json.loads(raw_details) if raw_details else {}
    except (TypeError, ValueError):
        return raw_details


def serialize_details(details):
    if isinstance(details, (dict, list)):
        return json.dumps(details)
    if details is None:
        return json.dumps({})
    return str(details)


def event_to_dict(event):
    return {
        "id": event.id,
        "url_id": getattr(event, "url_id", None),
        "user_id": getattr(event, "user_id", None),
        "event_type": normalize_event_type(event.event_type),
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "details": parse_details(event.details),
    }


@events_bp.route("/events", methods=["GET", "POST"])
def events_collection():
    if request.method == "GET":
        query = Event.select().order_by(Event.timestamp.desc(), Event.id.desc())

        raw_url_id = request.args.get("url_id")
        raw_user_id = request.args.get("user_id")
        raw_event_type = request.args.get("event_type")

        if raw_url_id is not None:
            url_id = parse_int(raw_url_id)
            if url_id is None:
                return jsonify({"error": "url_id must be an integer"}), 400
            query = query.where(Event.url_id == url_id)

        if raw_user_id is not None:
            user_id = parse_int(raw_user_id)
            if user_id is None:
                return jsonify({"error": "user_id must be an integer"}), 400
            query = query.where(Event.user_id == user_id)

        if raw_event_type is not None:
            event_type = normalize_event_type(raw_event_type)
            if not event_type:
                return jsonify({"error": "event_type cannot be empty"}), 400
            query = query.where(Event.event_type.in_([event_type, raw_event_type]))

        events = query.limit(100)
        return jsonify([event_to_dict(e) for e in events]), 200

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    raw_url_id = data.get("url_id")
    raw_user_id = data.get("user_id")
    raw_event_type = data.get("event_type")
    details = data.get("details", {})

    if raw_url_id is None or raw_event_type is None:
        return jsonify({"error": "url_id and event_type are required"}), 400

    url_id = parse_int(raw_url_id)
    if url_id is None:
        return jsonify({"error": "url_id must be an integer"}), 400

    event_type = normalize_event_type(raw_event_type)
    if not event_type:
        return jsonify({"error": "event_type cannot be empty"}), 400

    if event_type not in ALLOWED_EVENT_TYPES:
        return jsonify({"error": "invalid event_type"}), 400

    url = URL.get_or_none(URL.id == url_id)
    if not url:
        return jsonify({"error": f"URL {url_id} not found"}), 404

    user_id = None
    if raw_user_id is not None:
        user_id = parse_int(raw_user_id)
        if user_id is None:
            return jsonify({"error": "user_id must be an integer"}), 400

        user = User.get_or_none(User.id == user_id)
        if not user:
            return jsonify({"error": f"User {user_id} not found"}), 404

    details_value = serialize_details(details)

    try:
        event = Event.create(
            url_id=url_id,
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime.datetime.utcnow(),
            details=details_value,
        )
    except IntegrityError:
        return jsonify({"error": "could not create event"}), 409

    return jsonify(event_to_dict(event)), 201