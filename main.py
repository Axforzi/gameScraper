"""Application entry point: serve the Flask app with Waitress (REQ-CFG-3).

Package imports resolve through the installed distribution (``pip install -e .``)
— no import-path manipulation (REQ-PKG-1). Host, port, and the secret come
from environment-backed settings.

An optional ``.env`` file in the working directory is loaded first so local
development and simple deploys do not need exported variables; real
environment variables always take precedence over the file (python-dotenv
default, ``override=False``).
"""

from dotenv import load_dotenv
from waitress import serve

from src.app import create_app
from src.config import Settings

if __name__ == "__main__":
    load_dotenv()
    settings = Settings.from_env()
    app = create_app(settings)
    print(
        f"Serving on http://{settings.host}:{settings.port} "
        f"(Waitress, debug={settings.debug})",
        flush=True,
    )
    serve(
        app,
        host=settings.host,
        port=settings.port,
        threads=settings.waitress_threads,
    )
