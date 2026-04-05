# Incident Response Runbook

## Alert: Service Down

### Meaning
The service is unreachable or failing health checks.

### Steps
1. Check running containers:
   docker ps

2. Check logs:
   docker logs app-instance-1 --tail 50

3. Restart services:
   docker compose up -d

4. Verify recovery:
   curl http://localhost:5001/health

---

## Alert: High CPU Usage

### Meaning
System is under heavy load and may degrade performance.

### Steps
1. Check metrics:
   curl http://localhost:5001/metrics

2. Check container usage:
   docker stats --no-stream

3. Restart affected instance:
   docker compose restart app1

4. Monitor Grafana for recovery

---

## Alert: High Error Rate (5xx)

### Meaning
The application is failing requests.

### Steps
1. Check logs:
   docker logs app-instance-1 --tail 100

2. Check database:
   docker exec hackathon-db-compose pg_isready -U postgres

3. Check Redis:
   docker exec redis-cache redis-cli ping

4. Restart services if needed:
   docker compose restart

---

## Alert: Database Failure

### Meaning
Database is unavailable or rejecting connections.

### Steps
1. Restart database:
   docker compose restart db

2. Wait for healthcheck

3. Verify:
   curl http://localhost:5001/health