"""Flask application factory (REQ-PKG-1, REQ-CFG-2).

``create_app()`` builds and configures the app. The Tier 1 module-level ``app``
is replaced by the factory; the entry point (``main.py``) consumes it and
serves it with Waitress.
"""

from flask import Flask, jsonify
from flask_wtf.csrf import CSRFError, CSRFProtect

from src.config import Settings
from src.routes.index import index

_DEV_FALLBACK_SECRET = "dev-only-insecure-secret"


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings.from_env()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.secret_key or _DEV_FALLBACK_SECRET
    if not settings.secret_key:
        app.logger.warning(
            "SECRET_KEY not set; using an insecure dev fallback (DEBUG mode only). "
            "Set SECRET_KEY in the environment before deploying."
        )
    app.config["SPIDER_TIMEOUT"] = settings.spider_timeout
    app.config["CURRENCY"] = settings.currency
    app.config["DEBUG"] = settings.debug

    # CSRF protection for all POST endpoints
    CSRFProtect(app)

    app.register_blueprint(index)
    app.register_error_handler(CSRFError, handle_csrf_error)
    return app


def handle_csrf_error(error):
    return jsonify({"error": "CSRF validation failed"}), 400
