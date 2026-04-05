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


# ==========================================
# --- Health ---
# ==========================================

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


# ==========================================
# --- URLs & Redirects ---
# ==========================================

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

def test_post_urls_alias(client):
    res = client.post("/urls", json={"original_url": "https://example-alias.com"})
    assert res.status_code == 201

def test_list_urls(client):
    client.post("/shorten", json={"original_url": "https://example.com"})
    res = client.get("/urls")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)
    assert len(res.get_json()) > 0

def test_list_urls_filtered(client):
    res = client.post("/shorten", json={"original_url": "https://filter-test.com"})
    url_id = res.get_json()["id"]
    client.put(f"/urls/{url_id}", json={"is_active": False})
    
    res_inactive = client.get("/urls?is_active=false")
    assert res_inactive.status_code == 200
    assert all(u["is_active"] is False for u in res_inactive.get_json())
    
    res_bad_filter = client.get("/urls?is_active=notabool")
    assert res_bad_filter.status_code == 400

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

def test_update_url(client):
    res = client.post("/shorten", json={"original_url": "https://example.com"})
    url_id = res.get_json()["id"]
    
    update_res = client.put(f"/urls/{url_id}", json={"title": "Updated Title", "is_active": False})
    assert update_res.status_code == 200
    data = update_res.get_json()
    assert data["title"] == "Updated Title"
    assert data["is_active"] is False

def test_update_url_errors(client):
    res = client.post("/shorten", json={"original_url": "https://example.com"})
    url_id = res.get_json()["id"]
    
    assert client.put(f"/urls/{url_id}", json={}).status_code == 400 # no updatable fields
    assert client.put(f"/urls/{url_id}", json={"original_url": ""}).status_code == 400
    assert client.put(f"/urls/{url_id}", json={"is_active": "invalid"}).status_code == 400

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


# ==========================================
# --- Users ---
# ==========================================

def test_list_users(client):
    res = client.get("/users")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)

def test_list_users_pagination(client):
    client.post("/users", json={"username": "page_user", "email": "page@test.com"})
    res = client.get("/users?page=1&per_page=1")
    assert res.status_code == 200
    assert len(res.get_json()) == 1

def test_list_users_pagination_error(client):
    res = client.get("/users?page=-1&per_page=5")
    assert res.status_code == 400

def test_create_user(client):
    res = client.post("/users", json={"username": "newuser", "email": "new@test.com"})
    assert res.status_code == 201
    assert res.get_json()["username"] == "newuser"

def test_create_user_errors(client):
    assert client.post("/users", json={"username": "missing_email"}).status_code == 400
    assert client.post("/users", data="not json").status_code == 400
    
    # Duplicate
    client.post("/users", json={"username": "dup_user", "email": "dup@test.com"})
    res = client.post("/users", json={"username": "dup_user", "email": "dup@test.com"})
    assert res.status_code == 409

def test_get_user_by_id(client):
    create_res = client.post("/users", json={"username": "getme", "email": "getme@test.com"})
    u_id = create_res.get_json()["id"]
    res = client.get(f"/users/{u_id}")
    assert res.status_code == 200
    assert res.get_json()["username"] == "getme"

def test_get_user_not_found(client):
    res = client.get("/users/999999")
    assert res.status_code == 404
    assert "error" in res.get_json()

def test_update_user(client):
    create_res = client.post("/users", json={"username": "updateme", "email": "update@test.com"})
    u_id = create_res.get_json()["id"]
    res = client.put(f"/users/{u_id}", json={"username": "new_name"})
    assert res.status_code == 200
    assert res.get_json()["username"] == "new_name"

def test_update_user_errors(client):
    create_res = client.post("/users", json={"username": "err_user", "email": "err@test.com"})
    u_id = create_res.get_json()["id"]
    assert client.put(f"/users/{u_id}", json={}).status_code == 400
    assert client.put(f"/users/{u_id}", json={"username": ""}).status_code == 400

def test_delete_user(client):
    create_res = client.post("/users", json={"username": "delme", "email": "delme@test.com"})
    u_id = create_res.get_json()["id"]
    assert client.delete(f"/users/{u_id}").status_code == 204
    assert client.get(f"/users/{u_id}").status_code == 404

def test_bulk_users_path_traversal(client):
    res = client.post("/users/bulk", data='{"file": "../../../etc/passwd"}')
    assert res.status_code == 404 # Safely looks for "passwd" in root and 404s


# ==========================================
# --- Events ---
# ==========================================

def test_list_events(client):
    res = client.get("/events")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)

def test_create_event_valid(client):
    url_res = client.post("/shorten", json={"original_url": "https://event-test.com"})
    url_id = url_res.get_json()["id"]

    res = client.post("/events", json={
        "url_id": url_id,
        "event_type": "click",
        "details": {"source": "direct_test"}
    })
    
    assert res.status_code == 201
    data = res.get_json()
    assert data["event_type"] == "click"
    assert data["url_id"] == url_id

def test_create_event_errors(client):
    assert client.post("/events", json={"event_type": "click"}).status_code == 400 # missing url_id
    assert client.post("/events", json={"url_id": 99999, "event_type": "click"}).status_code == 404 # bad url
    
    url_res = client.post("/shorten", json={"original_url": "https://test.com"})
    url_id = url_res.get_json()["id"]
    assert client.post("/events", json={"url_id": url_id, "event_type": "invalid_type"}).status_code == 400

def test_list_events_filtered(client):
    url_res = client.post("/shorten", json={"original_url": "https://filter-event.com"})
    url_id = url_res.get_json()["id"]
    
    # URL creation triggers a "created" event, so there should be at least one
    res_url_filter = client.get(f"/events?url_id={url_id}")
    assert res_url_filter.status_code == 200
    assert len(res_url_filter.get_json()) > 0
    
    res_type_filter = client.get("/events?event_type=created")
    assert res_type_filter.status_code == 200
    assert all(e["event_type"] == "created" for e in res_type_filter.get_json())

def test_list_events_filter_errors(client):
    assert client.get("/events?url_id=invalid").status_code == 400
    assert client.get("/events?event_type=").status_code == 400
