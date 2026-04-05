from dotenv import load_dotenv
from flask import Flask, jsonify
import os
import psutil

from app.database import init_db
from app.routes import register_routes


def create_app():
    load_dotenv()

    app = Flask(__name__)

    init_db(app)

    from app import models  # noqa: F401 - registers models with Peewee

    register_routes(app)

    @app.route("/health")
    def health():
        return jsonify(status="ok")
    
    @app.route("/metrics", methods=["GET"])
    def metrics():
        process = psutil.Process(os.getpid())
        return jsonify({
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "process_memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "process_threads": process.num_threads(),
        }), 200
    

    return app
