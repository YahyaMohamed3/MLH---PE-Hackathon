# MLH PE Hackathon — URL Shortener

A production-grade URL shortener built with Flask, PostgreSQL, and Peewee ORM. Built for the MLH Production Engineering Hackathon.

## Stack

- **Backend:** Flask + Peewee ORM
- **Database:** PostgreSQL
- **Testing:** pytest + pytest-cov
- **CI:** GitHub Actions
- **Package Manager:** uv

## Architecture

```

User → Flask App → PostgreSQL
→ Events Log

````

## Quick Start

**Prerequisites:** Docker Desktop, Python 3.11+, uv

```bash
# 1. Clone
git clone https://github.com/YahyaMohamed3/MLH---PE-Hackathon.git
cd MLH---PE-Hackathon

# 2. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies
uv sync

# 4. Start PostgreSQL
docker run --name hackathon-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=hackathon_db \
  -p 5433:5432 -d postgres

# 5. Configure environment
cp .env.example .env  # edit if needed

# 6. Seed the database
uv run seed.py

# 7. Run the server
uv run run.py
````

Visit `http://localhost:5000/health` — you should see `{"status": "ok"}`.

## Docker

```bash
docker compose up -d --build
curl http://localhost:5000/health
```

## Chaos Mode (Resilience Test)

```bash
docker exec reliability-app sh -c "kill 1"
sleep 3
docker compose ps
curl http://localhost:5000/health
```

Expected behavior:

* Container restarts automatically (`restart: always`)
* Service recovers without manual intervention
* `/health` returns `{"status": "ok"}`

## API Endpoints

| Method | Endpoint              | Description               |
| ------ | --------------------- | ------------------------- |
| GET    | `/health`             | Health check              |
| POST   | `/shorten`            | Create a short URL        |
| GET    | `/<short_code>`       | Redirect to original URL  |
| GET    | `/urls`               | List all URLs             |
| GET    | `/urls/<id>`          | Get a specific URL        |
| DELETE | `/urls/<id>`          | Deactivate a URL          |
| GET    | `/stats/<short_code>` | Get click stats for a URL |
| GET    | `/users`              | List all users            |
| GET    | `/users/<id>`         | Get a specific user       |

### POST /shorten

**Request:**

```json
{
  "original_url": "https://example.com",
  "title": "Example Site",
  "user_id": 1
}
```

**Response (201):**

```json
{
  "id": 1,
  "short_code": "abc123",
  "original_url": "https://example.com",
  "title": "Example Site",
  "is_active": true,
  "created_at": "2026-04-04T00:00:00"
}
```

**Error responses:**

* `400` — missing or invalid URL
* `404` — user_id not found

### GET /<short_code>

* `302` — redirects to original URL
* `404` — short code not found
* `410` — URL has been deactivated

## Environment Variables

| Variable            | Default        | Description              |
| ------------------- | -------------- | ------------------------ |
| `DATABASE_NAME`     | `hackathon_db` | PostgreSQL database name |
| `DATABASE_HOST`     | `localhost`    | Database host            |
| `DATABASE_PORT`     | `5432`         | Database port            |
| `DATABASE_USER`     | `postgres`     | Database user            |
| `DATABASE_PASSWORD` | `postgres`     | Database password        |
| `FLASK_DEBUG`       | `true`         | Enable debug mode        |

## Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ --cov=app --cov-report=term-missing
```

Current coverage: **99%** (165 statements, 2 missed)

## CI/CD

GitHub Actions runs on every push:

1. Spins up a PostgreSQL service container
2. Installs dependencies via uv
3. Runs all 23 tests
4. Enforces 70% minimum coverage
5. Blocks merge if any test fails

## Error Handling

| Scenario               | Response                                                            |
| ---------------------- | ------------------------------------------------------------------- |
| Missing `original_url` | `400 {"error": "original_url is required"}`                         |
| Invalid URL format     | `400 {"error": "original_url must start with http:// or https://"}` |
| Non-JSON request body  | `400 {"error": "Request body must be JSON"}`                        |
| Short code not found   | `404 {"error": "Short code '...' not found"}`                       |
| Deactivated URL        | `410 {"error": "This link has been deactivated"}`                   |
| User not found         | `404 {"error": "User ... not found"}`                               |

All errors return JSON — no stack traces exposed to users.

## Failure Modes

See `FAILURE_MODES.md` for detailed breakdown of:

* Database connection failures
* Invalid input handling
* API error responses
* Container crash and recovery behavior

## Capacity Plan

Current system design:

* Single Flask instance (development server)
* PostgreSQL as primary datastore

Estimated capacity:

* ~50–100 requests per second under light load

Known bottlenecks:

* Flask development server is not optimized for concurrency
* Database connection latency under load

Scaling plan:

* Replace Flask dev server with Gunicorn (multiple workers)
* Add Nginx reverse proxy
* Horizontally scale with multiple containers
* Introduce connection pooling and caching layer if needed

## Troubleshooting

**`password authentication failed for user "postgres"`**

* A local PostgreSQL may be running on port 5432. We use port 5433 to avoid conflicts.
* Run: `docker run ... -p 5433:5432 -d postgres`

**`uv: command not found`**

* Run: `source $HOME/.local/bin/env`
* Or restart your terminal after installing uv.

**`duplicate key value violates unique constraint`**

* The DB sequence is out of sync after seeding with explicit IDs.
* Fix: `docker exec -it hackathon-db psql -U postgres -d hackathon_db -c "SELECT setval('urls_id_seq', (SELECT MAX(id) FROM urls));"`

## Decision Log

| Decision                | Why                                                                                |
| ----------------------- | ---------------------------------------------------------------------------------- |
| Flask                   | Lightweight, minimal boilerplate, matches template                                 |
| Peewee ORM              | Simple, lightweight ORM that fits the template's existing setup                    |
| PostgreSQL              | Reliable, production-grade relational DB with strong consistency                   |
| No FK constraints in DB | Seed data had referential inconsistencies; integrity enforced at app layer instead |
| pytest                  | Industry standard, integrates well with Flask test client                          |
| uv                      | Fast dependency management, handles Python versions automatically                  |
| Port 5433 locally       | Avoids conflict with any existing local PostgreSQL on 5432                         |


