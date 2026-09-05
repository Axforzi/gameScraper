"""Shared fixtures for the gamescraper test suite (REQ-TST-1).

Crochet constraint: only ONE reactor per process. ``crochet.setup()`` runs at
``src.triggers`` import time; importing the module here guarantees the reactor
exists before any test needs it, and every later ``setup()`` call is a no-op.
No test starts a second reactor — spiders are mocked or fed the cached
fixtures under ``tests/fixtures/``, never live sites (REQ-TST-4).
"""

import os
import pathlib

import pytest

import src.triggers
from src.app import create_app
from src.config import Settings

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True, scope="session")
def _suite_env():
    """Default SECRET_KEY for the whole session; tests may override it."""
    os.environ.setdefault("SECRET_KEY", "test-secret-key")
    yield


@pytest.fixture(scope="session")
def crochet_reactor():
    """Return the triggers module after its import-time ``crochet.setup()``.

    Request this fixture in tests that drive the reactor bridge (e.g. the
    TriggerRunner cancel path) to make the single-reactor dependency explicit.
    """
    return src.triggers


@pytest.fixture()
def app():
    return create_app(Settings(secret_key="test-secret-key", debug=True))


@pytest.fixture()
def client(app):
    return app.test_client()


def read_fixture(relative_path: str) -> bytes:
    """Read a cached fixture file from ``tests/fixtures/`` as bytes."""
    return (FIXTURES_DIR / relative_path).read_bytes()