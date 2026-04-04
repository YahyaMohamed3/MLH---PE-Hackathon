import pytest
import os
os.environ["DATABASE_NAME"] = "hackathon_db"
os.environ["DATABASE_HOST"] = "localhost"
os.environ["DATABASE_PORT"] = os.environ.get("DATABASE_PORT", "5433")
os.environ["DATABASE_USER"] = "postgres"
os.environ["DATABASE_PASSWORD"] = "postgres"

from app import create_app
from app.database import db
from app.models.user import User
from app.models.url import URL
from app.models.event import Event


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_tables([User, URL, Event], safe=True)
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


# --- Health ---

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


# --- POST /shorten ---

def test_shorten_valid(client):
    res = client.post("/shorten", json={"original_url": "https://example.com"})
    assert res.status_code == 201
    data = res.get_json()
    assert "short_code" in data
    assert data["is_active"] is True
    assert data["original_url"] == "https://example.com"


def test_shorten_with_title(client):
    res = client.post("/shorten", json={"original_url": "https://example.com", "title": "Example"})
    assert res.status_code == 201
    assert res.get_json()["title"] == "Example"


def test_shorten_missing_url(client):
    res = client.post("/shorten", json={})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_shorten_invalid_url(client):
    res = client.post("/shorten", json={"original_url": "not-a-url"})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_shorten_empty_url(client):
    res = client.post("/shorten", json={"original_url": ""})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_shorten_no_json(client):
    res = client.post("/shorten", data="not json", content_type="text/plain")
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_shorten_http_url(client):
    res = client.post("/shorten", json={"original_url": "http://example.com"})
    assert res.status_code == 201


def test_shorten_unique_codes(client):
    res1 = client.post("/shorten", json={"original_url": "https://example.com"})
    res2 = client.post("/shorten", json={"original_url": "https://example.com"})
    assert res1.get_json()["short_code"] != res2.get_json()["short_code"]


def test_shorten_invalid_user(client):
    res = client.post("/shorten", json={"original_url": "https://example.com", "user_id": 999999})
    assert res.status_code == 404
    assert "error" in res.get_json()


# --- GET /<short_code> redirect ---

def test_redirect_valid(client):
    res = client.post("/shorten", json={"original_url": "https://example.com"})
    code = res.get_json()["short_code"]
    res = client.get(f"/{code}")
    assert res.status_code == 302
    assert "example.com" in res.headers["Location"]


def test_redirect_not_found(client):
    res = client.get("/doesnotexist99")
    assert res.status_code == 404
    assert "error" in res.get_json()


def test_redirect_increments_click_count(client):
    res = client.post("/shorten", json={"original_url": "https://example.com"})
    code = res.get_json()["short_code"]
    client.get(f"/{code}")
    client.get(f"/{code}")
    urls = client.get("/urls").get_json()
    url = next(u for u in urls if u["short_code"] == code)
    assert url["click_count"] == 2


def test_redirect_deactivated(client):
    res = client.post("/shorten", json={"original_url": "https://example.com"})
    url_id = res.get_json()["id"]
    code = res.get_json()["short_code"]
    client.delete(f"/urls/{url_id}")
    res = client.get(f"/{code}")
    assert res.status_code == 410
    assert "error" in res.get_json()


# --- GET /urls ---

def test_list_urls(client):
    client.post("/shorten", json={"original_url": "https://example.com"})
    res = client.get("/urls")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)
    assert len(res.get_json()) > 0


# --- GET /urls/<id> ---

def test_get_url_by_id(client):
    res = client.post("/shorten", json={"original_url": "https://example.com"})
    url_id = res.get_json()["id"]
    res = client.get(f"/urls/{url_id}")
    assert res.status_code == 200
    assert res.get_json()["id"] == url_id


def test_get_url_not_found(client):
    res = client.get("/urls/999999")
    assert res.status_code == 404
    assert "error" in res.get_json()


# --- DELETE /urls/<id> ---

def test_deactivate_url(client):
    res = client.post("/shorten", json={"original_url": "https://example.com"})
    url_id = res.get_json()["id"]
    res = client.delete(f"/urls/{url_id}")
    assert res.status_code == 200
    res = client.get(f"/urls/{url_id}")
    assert res.get_json()["is_active"] is False


def test_deactivate_not_found(client):
    res = client.delete("/urls/999999")
    assert res.status_code == 404
    assert "error" in res.get_json()


# --- GET /stats/<short_code> ---

def test_stats_valid(client):
    res = client.post("/shorten", json={"original_url": "https://example.com"})
    code = res.get_json()["short_code"]
    res = client.get(f"/stats/{code}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["short_code"] == code
    assert "click_count" in data
    assert "events" in data


def test_stats_not_found(client):
    res = client.get("/stats/doesnotexist")
    assert res.status_code == 404
    assert "error" in res.get_json()


# --- GET /users ---

def test_list_users(client):
    res = client.get("/users")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_get_user_not_found(client):
    res = client.get("/users/999999")
    assert res.status_code == 404
    assert "error" in res.get_json()