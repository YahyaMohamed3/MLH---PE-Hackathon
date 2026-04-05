import datetime
import json
import os
import random
import string

import redis
from flask import Blueprint, jsonify, redirect, request
from peewee import IntegrityError

from app.models.event import Event
from app.models.url import URL
from app.models.user import User

urls_bp = Blueprint("urls", __name__)

try:
    cache = redis.Redis(
        host=os.environ.get("REDIS_HOST", "redis-cache"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        decode_responses=True,
        socket_connect_timeout=2,
    )
    cache.ping()
except Exception:
    cache = None


def get_cache(key):
    if not cache:
        return None
    try:
        val = cache.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def set_cache(key, value, ttl=60):
    if not cache:
        return
    try:
        cache.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def delete_cache(*keys):
    if not cache:
        return
    try:
        for key in keys:
            cache.delete(key)
    except Exception:
        pass


def parse_bool(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def parse_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_text(value):
    return str(value or "").strip()


def is_valid_url(url):
    return bool(url and (url.startswith("http://") or url.startswith("https://")))


def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    while True:
        code = "".join(random.choices(chars, k=length))
        if not URL.select().where(URL.short_code == code).exists():
            return code


def url_to_dict(url):
    return {
        "id": url.id,
        "user_id": getattr(url, "user_id", None),
        "short_code": url.short_code,
        "original_url": url.original_url,
        "title": url.title,
        "is_active": url.is_active,
        "click_count": url.click_count,
        "created_at": url.created_at.isoformat() if url.created_at else None,
        "updated_at": url.updated_at.isoformat() if url.updated_at else None,
    }


def create_url_record(original_url, title=None, user_id=None):
    if not original_url:
        return {"error": "original_url is required"}, 400

    if not is_valid_url(original_url):
        return {"error": "original_url must start with http:// or https://"}, 400

    resolved_user_id = None
    if user_id is not None:
        resolved_user_id = parse_int(user_id)
        if resolved_user_id is None:
            return {"error": "user_id must be an integer"}, 400

        user = User.get_or_none(User.id == resolved_user_id)
        if not user:
            return {"error": f"User {resolved_user_id} not found"}, 404

    short_code = generate_short_code()
    now = datetime.datetime.utcnow()

    try:
        url = URL.create(
            user_id=resolved_user_id,
            short_code=short_code,
            original_url=original_url,
            title=title or None,
            is_active=True,
            click_count=0,
            created_at=now,
            updated_at=now,
        )
    except IntegrityError:
        return {"error": "could not create url"}, 409

    Event.create(
        url_id=url.id,
        user_id=resolved_user_id,
        event_type="created",
        timestamp=now,
        details=json.dumps({
            "short_code": short_code,
            "original_url": original_url,
        }),
    )

    delete_cache("urls:list", "urls:list:active:true", "urls:list:active:false", f"urls:list:user:{resolved_user_id}")
    return url_to_dict(url), 201


@urls_bp.route("/shorten", methods=["POST"])
def shorten_url():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    result, status = create_url_record(
        original_url=normalize_text(data.get("original_url")),
        title=normalize_text(data.get("title")),
        user_id=data.get("user_id"),
    )
    return jsonify(result), status


@urls_bp.route("/urls", methods=["GET", "POST"])
def urls_collection():
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "request body must be a JSON object"}), 400

        result, status = create_url_record(
            original_url=normalize_text(data.get("original_url")),
            title=normalize_text(data.get("title")),
            user_id=data.get("user_id"),
        )
        return jsonify(result), status

    query = URL.select().order_by(URL.created_at.desc())

    raw_user_id = request.args.get("user_id")
    raw_is_active = request.args.get("is_active")

    if raw_user_id is not None:
        user_id = parse_int(raw_user_id)
        if user_id is None:
            return jsonify({"error": "user_id must be an integer"}), 400
        query = query.where(URL.user_id == user_id)

    if raw_is_active is not None:
        is_active = parse_bool(raw_is_active)
        if is_active is None:
            return jsonify({"error": "is_active must be true or false"}), 400
        query = query.where(URL.is_active == is_active)

    urls = query.limit(100)
    return jsonify([url_to_dict(u) for u in urls]), 200


@urls_bp.route("/urls/<int:url_id>", methods=["GET", "PUT", "DELETE"])
def url_detail(url_id):
    url = URL.get_or_none(URL.id == url_id)
    if not url:
        return jsonify({"error": f"URL {url_id} not found"}), 404

    if request.method == "GET":
        return jsonify(url_to_dict(url)), 200

    if request.method == "PUT":
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "request body must be a JSON object"}), 400

        original_url = data.get("original_url")
        title = data.get("title")
        is_active = data.get("is_active")
        user_id = data.get("user_id")

        if all(field is None for field in [original_url, title, is_active, user_id]):
            return jsonify({"error": "at least one updatable field is required"}), 400

        old_is_active = url.is_active

        if original_url is not None:
            original_url = normalize_text(original_url)
            if not original_url:
                return jsonify({"error": "original_url cannot be empty"}), 400
            if not is_valid_url(original_url):
                return jsonify({"error": "original_url must start with http:// or https://"}), 400
            url.original_url = original_url

        if title is not None:
            url.title = normalize_text(title) or None

        if is_active is not None:
            if not isinstance(is_active, bool):
                parsed = parse_bool(is_active)
                if parsed is None:
                    return jsonify({"error": "is_active must be true or false"}), 400
                is_active = parsed
            url.is_active = is_active

        if user_id is not None:
            if user_id == "":
                url.user_id = None
            else:
                resolved_user_id = parse_int(user_id)
                if resolved_user_id is None:
                    return jsonify({"error": "user_id must be an integer"}), 400

                user = User.get_or_none(User.id == resolved_user_id)
                if not user:
                    return jsonify({"error": f"User {resolved_user_id} not found"}), 404
                url.user_id = resolved_user_id

        url.updated_at = datetime.datetime.utcnow()

        try:
            url.save()
        except IntegrityError:
            return jsonify({"error": "could not update url"}), 409

        event_type = "updated"
        if old_is_active and not url.is_active:
            event_type = "deactivated"

        Event.create(
            url_id=url.id,
            user_id=url.user_id,
            event_type=event_type,
            timestamp=datetime.datetime.utcnow(),
            details=json.dumps({
                "title": url.title,
                "is_active": url.is_active,
                "original_url": url.original_url,
            }),
        )

        delete_cache("urls:list", "urls:list:active:true", "urls:list:active:false", f"urls:list:user:{url.user_id}", f"url:{url.short_code}")
        return jsonify(url_to_dict(url)), 200

    URL.update(
        is_active=False,
        updated_at=datetime.datetime.utcnow()
    ).where(URL.id == url_id).execute()

    Event.create(
        url_id=url.id,
        user_id=url.user_id,
        event_type="deactivated",
        timestamp=datetime.datetime.utcnow(),
        details=json.dumps({"short_code": url.short_code}),
    )

    delete_cache("urls:list", "urls:list:active:true", "urls:list:active:false", f"urls:list:user:{url.user_id}", f"url:{url.short_code}")
    return jsonify({"message": f"URL {url_id} deactivated"}), 200


@urls_bp.route("/<short_code>", methods=["GET"])
def redirect_url(short_code):
    short_code = normalize_text(short_code)
    if not short_code or len(short_code) > 20:
        return jsonify({"error": "Invalid short code"}), 400

    cached = get_cache(f"url:{short_code}")
    if cached:
        if not cached.get("is_active"):
            return jsonify({"error": "This link has been deactivated"}), 410

        URL.update(
            click_count=URL.click_count + 1,
            updated_at=datetime.datetime.utcnow()
        ).where(URL.short_code == short_code).execute()

        Event.create(
            url_id=cached["id"],
            user_id=cached.get("user_id"),
            event_type="click",
            timestamp=datetime.datetime.utcnow(),
            details=json.dumps({"short_code": short_code, "source": "cache"}),
        )
        return redirect(cached["original_url"], code=302)

    url = URL.get_or_none(URL.short_code == short_code)
    if not url:
        return jsonify({"error": f"Short code '{short_code}' not found"}), 404

    if not url.is_active:
        return jsonify({"error": "This link has been deactivated"}), 410

    set_cache(f"url:{short_code}", {
        "id": url.id,
        "user_id": url.user_id,
        "original_url": url.original_url,
        "is_active": url.is_active,
    }, ttl=300)

    URL.update(
        click_count=URL.click_count + 1,
        updated_at=datetime.datetime.utcnow()
    ).where(URL.id == url.id).execute()

    Event.create(
        url_id=url.id,
        user_id=url.user_id,
        event_type="click",
        timestamp=datetime.datetime.utcnow(),
        details=json.dumps({"short_code": short_code}),
    )

    return redirect(url.original_url, code=302)


@urls_bp.route("/stats/<short_code>", methods=["GET"])
def get_stats(short_code):
    short_code = normalize_text(short_code)
    url = URL.get_or_none(URL.short_code == short_code)
    if not url:
        return jsonify({"error": f"Short code '{short_code}' not found"}), 404

    events = (
        Event
        .select()
        .where(Event.url_id == url.id)
        .order_by(Event.timestamp.desc())
        .limit(50)
    )

    return jsonify({
        "short_code": url.short_code,
        "original_url": url.original_url,
        "title": url.title,
        "is_active": url.is_active,
        "click_count": url.click_count,
        "events": [{
            "event_type": e.event_type,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        } for e in events],
    }), 200