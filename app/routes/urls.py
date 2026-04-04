import datetime
import json
import random
import string

from flask import Blueprint, jsonify, redirect, request

from app.models.event import Event
from app.models.url import URL
from app.models.user import User

urls_bp = Blueprint("urls", __name__)


def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    while True:
        code = "".join(random.choices(chars, k=length))
        if not URL.select().where(URL.short_code == code).exists():
            return code


def is_valid_url(url):
    return url and (url.startswith("http://") or url.startswith("https://"))


@urls_bp.route("/shorten", methods=["POST"])
def shorten_url():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    original_url = data.get("original_url", "").strip()
    title = data.get("title", "").strip()
    user_id = data.get("user_id")

    if not original_url:
        return jsonify({"error": "original_url is required"}), 400
    if not is_valid_url(original_url):
        return jsonify({"error": "original_url must start with http:// or https://"}), 400

    # Validate user if provided
    if user_id:
        try:
            User.get_by_id(int(user_id))
        except User.DoesNotExist:
            return jsonify({"error": f"User {user_id} not found"}), 404

    short_code = generate_short_code()
    url = URL.create(
        user_id=int(user_id) if user_id else None,
        short_code=short_code,
        original_url=original_url,
        title=title or None,
        is_active=True,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
    )

    Event.create(
        url_id=url.id,
        user_id=int(user_id) if user_id else None,
        event_type="created",
        timestamp=datetime.datetime.now(),
        details=json.dumps({"short_code": short_code, "original_url": original_url}),
    )

    return jsonify({
        "id": url.id,
        "short_code": url.short_code,
        "original_url": url.original_url,
        "title": url.title,
        "is_active": url.is_active,
        "created_at": url.created_at.isoformat(),
    }), 201


@urls_bp.route("/<short_code>", methods=["GET"])
def redirect_url(short_code):
    if not short_code or len(short_code) > 20:
        return jsonify({"error": "Invalid short code"}), 400
    try:
        url = URL.get(URL.short_code == short_code)
    except URL.DoesNotExist:
        return jsonify({"error": f"Short code '{short_code}' not found"}), 404

    if not url.is_active:
        return jsonify({"error": "This link has been deactivated"}), 410

    URL.update(
        click_count=URL.click_count + 1,
        updated_at=datetime.datetime.now()
    ).where(URL.id == url.id).execute()

    Event.create(
        url_id=url.id,
        user_id=None,
        event_type="clicked",
        timestamp=datetime.datetime.now(),
        details=json.dumps({"short_code": short_code}),
    )

    return redirect(url.original_url, code=302)


@urls_bp.route("/urls", methods=["GET"])
def list_urls():
    urls = URL.select().order_by(URL.created_at.desc()).limit(100)
    return jsonify([{
        "id": u.id,
        "short_code": u.short_code,
        "original_url": u.original_url,
        "title": u.title,
        "is_active": u.is_active,
        "click_count": u.click_count,
        "created_at": u.created_at.isoformat(),
    } for u in urls])


@urls_bp.route("/urls/<int:url_id>", methods=["GET"])
def get_url(url_id):
    try:
        url = URL.get_by_id(url_id)
    except URL.DoesNotExist:
        return jsonify({"error": f"URL {url_id} not found"}), 404

    return jsonify({
        "id": url.id,
        "short_code": url.short_code,
        "original_url": url.original_url,
        "title": url.title,
        "is_active": url.is_active,
        "click_count": url.click_count,
        "created_at": url.created_at.isoformat(),
        "updated_at": url.updated_at.isoformat(),
    })


@urls_bp.route("/urls/<int:url_id>", methods=["DELETE"])
def deactivate_url(url_id):
    try:
        url = URL.get_by_id(url_id)
    except URL.DoesNotExist:
        return jsonify({"error": f"URL {url_id} not found"}), 404

    URL.update(
        is_active=False,
        updated_at=datetime.datetime.now()
    ).where(URL.id == url_id).execute()

    Event.create(
        url_id=url.id,
        user_id=None,
        event_type="deactivated",
        timestamp=datetime.datetime.now(),
        details=json.dumps({"short_code": url.short_code}),
    )

    return jsonify({"message": f"URL {url_id} deactivated"}), 200


@urls_bp.route("/stats/<short_code>", methods=["GET"])
def get_stats(short_code):
    try:
        url = URL.get(URL.short_code == short_code)
    except URL.DoesNotExist:
        return jsonify({"error": f"Short code '{short_code}' not found"}), 404

    events = (Event
              .select()
              .where(Event.url_id == url.id)
              .order_by(Event.timestamp.desc())
              .limit(50))

    return jsonify({
        "short_code": url.short_code,
        "original_url": url.original_url,
        "title": url.title,
        "is_active": url.is_active,
        "click_count": url.click_count,
        "events": [{
            "event_type": e.event_type,
            "timestamp": e.timestamp.isoformat(),
        } for e in events],
    })