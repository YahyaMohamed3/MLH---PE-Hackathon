# Failure Modes

## Overview
This service is designed to fail gracefully and recover from common failures. It includes automated tests, a `/health` endpoint, JSON error responses, and Docker auto-restart behavior.

## Failure Scenarios

### 1. Invalid input
Malformed or incomplete input should return a clean JSON error response.

**Expected result**
- HTTP 400
- JSON error body
- no unintended data changes

### 2. Unknown route
Requests to routes that do not exist should return a JSON 404 response.

**Expected result**
- HTTP 404
- JSON error body

### 3. Internal server error
Unexpected exceptions should return a JSON 500 response without exposing a traceback.

**Expected result**
- HTTP 500
- JSON error body
- no raw stack trace shown to the client

### 4. App/container crash
If the app container is killed, Docker restarts it automatically due to the restart policy.

**Expected result**
- container stops
- Docker restarts it
- `/health` becomes available again

## Health Check
`GET /health` returns `200 OK` when the service is running.

## Recovery Strategy
- tests run in CI
- broken code is blocked by CI
- graceful JSON errors prevent ugly crashes
- Docker restart policy restores service after process failure

## Limits
- if the host machine goes down, the app cannot restart until the host returns
- if external dependencies fail, related endpoints may still fail until recovery