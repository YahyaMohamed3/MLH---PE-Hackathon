from dotenv import load_dotenv
from flask import Flask, jsonify, Response
import os
import psutil

from app.database import create_tables, init_db
from app.routes import register_routes

from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST
)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['endpoint']
)
CPU_GAUGE = Gauge('system_cpu_percent', 'System CPU usage percent')
MEMORY_GAUGE = Gauge('system_memory_percent', 'System memory usage percent')
ACTIVE_REQUESTS = Gauge('http_active_requests', 'Active HTTP requests')


def create_app():
    load_dotenv()

    app = Flask(__name__)

    init_db(app)

    from app import models  # noqa: F401

    create_tables()

    register_routes(app)

    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def handle_405(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def handle_500(e):
        return jsonify({"error": "Internal server error"}), 500

    @app.before_request
    def before_request():
        ACTIVE_REQUESTS.inc()

    @app.after_request
    def after_request(response):
        ACTIVE_REQUESTS.dec()
        from flask import request
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
        return response

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    @app.route("/metrics", methods=["GET"])
    def metrics():
        process = psutil.Process(os.getpid())
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        CPU_GAUGE.set(cpu)
        MEMORY_GAUGE.set(mem)
        return jsonify({
            "cpu_percent": cpu,
            "memory_percent": mem,
            "process_memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "process_threads": process.num_threads(),
        }), 200

    @app.route("/metrics/prometheus", methods=["GET"])
    def metrics_prometheus():
        process = psutil.Process(os.getpid())
        CPU_GAUGE.set(psutil.cpu_percent(interval=0.1))
        MEMORY_GAUGE.set(psutil.virtual_memory().percent)
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    return app