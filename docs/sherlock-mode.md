# Sherlock Mode: Incident Diagnosis

## Incident
During testing, the database was intentionally stopped to simulate failure.

## Observations from Grafana
- Traffic remained stable
- Error Rate (5xx) increased sharply
- Active Requests increased
- CPU usage remained normal

## Investigation
Checked application logs:

docker logs app-instance-1

Found repeated errors:
peewee.OperationalError: connection refused

## Root Cause
PostgreSQL container was unavailable, causing all DB-dependent endpoints to fail.

## Resolution
Restarted the database:

docker compose restart db

## Result
- Error rate returned to zero
- Requests succeeded again
- System recovered fully