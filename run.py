from flask import request
import logging

from app import create_app
from app.utils.logging_config import setup_logging

setup_logging()
app = create_app()

logger = logging.getLogger(__name__)
logger.info("Application started", extra={"component": "startup"})

@app.before_request
def log_request():
    logger.info(
        f"{request.method} {request.path}",
        extra={"component": "http"}
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)