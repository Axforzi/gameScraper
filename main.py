"""Application entry point: serve the Flask app with Waitress (REQ-CFG-3).

Package imports resolve through the installed distribution (``pip install -e .``)
— no import-path manipulation (REQ-PKG-1). Host, port, and the secret come
from environment-backed settings.
"""

from waitress import serve

from src.app import create_app
from src.config import Settings

if __name__ == "__main__":
    settings = Settings.from_env()
    app = create_app(settings)
    serve(app, host=settings.host, port=settings.port)
