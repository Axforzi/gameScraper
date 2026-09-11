"""Route tests (REQ-SEC-2/3, REQ-ASM-3, REQ-TST-3).

``TriggerRunner`` is replaced by a scriptable fake via monkeypatch at the
``src.routes.index`` import site (the route module owns the name). The real
Flask app + Flask-WTF CSRF protection stays active: every POST test mirrors
the browser flow — GET the page first (same client, so the session cookie
carries the CSRF token), then extract the token from the meta tag.
"""

import re

import crochet
import pytest

from src.routes.index import (
    FAILED_JUEGO_MSG,
    FAILED_OFERTAS_MSG,
    GAME_SPIDERS,
    OFFER_SPIDERS,
    TIMEOUT_JUEGO_MSG,
    TIMEOUT_OFERTAS_MSG,
)

_CSRF_META = re.compile(rb'name="csrf-token" content="([^"]+)"')


class FakeTriggerRunner:
    """Scriptable stand-in: item payload, per-store errors, or a raised exc."""

    items: dict = {}
    errors: list = []
    raise_exc: type[Exception] | None = None
    launches: list[tuple] = []

    def __init__(self, spiders, term=None, timeout=None) -> None:
        FakeTriggerRunner.launches.append((tuple(spiders), term, timeout))

    def run(self) -> dict:
        if FakeTriggerRunner.raise_exc is not None:
            raise FakeTriggerRunner.raise_exc()
        return dict(FakeTriggerRunner.items)


@pytest.fixture()
def fake_trigger(monkeypatch):
    monkeypatch.setattr("src.routes.index.TriggerRunner", FakeTriggerRunner)
    return FakeTriggerRunner


@pytest.fixture(autouse=True)
def _reset_fake_trigger():
    FakeTriggerRunner.items = {}
    FakeTriggerRunner.errors = []
    FakeTriggerRunner.raise_exc = None
    FakeTriggerRunner.launches = []
    yield


def _csrf_token(client) -> str:
    response = client.get("/")
    assert response.status_code == 200
    match = _CSRF_META.search(response.data)
    assert match is not None, "meta csrf-token missing from index page"
    return match.group(1).decode()


def _post_juego(client, term: str, token: bytes):
    return client.post(
        "/juego",
        data={"game-link": term},
        headers={"X-CSRFToken": token},
    )


def test_get_index_renders_search_form(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert b'name="game-link"' in response.data
    assert b'name="csrf-token"' in response.data


def test_get_ofertas_page_renders(client) -> None:
    response = client.get("/ofertas")
    assert response.status_code == 200
    assert b'name="csrf-token"' in response.data


def test_post_juego_requires_csrf_token(client) -> None:
    response = client.post("/juego", data={"game-link": "half-life"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "CSRF validation failed"


def test_post_juego_success(fake_trigger, client) -> None:
    FakeTriggerRunner.items = {
        "steam": {"nombre": "Half-Life", "precio": 9.99},
        "gog": None,
        "egs": None,
    }
    token = _csrf_token(client)
    response = _post_juego(client, "half-life", token)

    assert response.status_code == 200
    assert response.get_json()["steam"]["nombre"] == "Half-Life"
    assert "error" not in response.get_json()


def test_post_juego_forwards_stripped_term_and_timeout(fake_trigger, client) -> None:
    token = _csrf_token(client)
    response = _post_juego(client, "  half-life  ", token)

    assert response.status_code == 200
    (spiders, term, timeout), *_ = FakeTriggerRunner.launches
    assert spiders == tuple(GAME_SPIDERS)
    assert term == "half-life"  # whitespace stripped before dispatch
    assert timeout == 60.0


def test_post_juego_validation_errors(client) -> None:
    token = _csrf_token(client)
    cases = [
        ({}, "obligatorio"),
        ({"game-link": "   "}, "vacío"),
        ({"game-link": "x" * 201}, "200 caracteres"),
        ({"game-link": "<script>"}, "no permitidos"),
    ]
    for payload, fragment in cases:
        response = client.post("/juego", data=payload, headers={"X-CSRFToken": token})
        assert response.status_code == 400
        assert fragment in response.get_json()["error"]


def test_post_juego_timeout_maps_504(fake_trigger, client) -> None:
    FakeTriggerRunner.raise_exc = crochet.TimeoutError
    FakeTriggerRunner.items = {"steam": {"nombre": "Partial"}}
    token = _csrf_token(client)
    response = _post_juego(client, "half-life", token)

    assert response.status_code == 504
    payload = response.get_json()
    assert payload["error"] == TIMEOUT_JUEGO_MSG
    assert payload["steam"]["nombre"] == "Partial"  # partial results preserved


def test_post_juego_trigger_failure_maps_502(fake_trigger, client) -> None:
    FakeTriggerRunner.raise_exc = RuntimeError
    token = _csrf_token(client)
    response = _post_juego(client, "half-life", token)

    assert response.status_code == 502
    assert response.get_json()["error"] == FAILED_JUEGO_MSG


def test_post_juego_total_failure_maps_502(fake_trigger, client) -> None:
    FakeTriggerRunner.items = {}
    FakeTriggerRunner.errors = [("SteamSpider", "page structure changed")]
    token = _csrf_token(client)
    response = _post_juego(client, "half-life", token)

    assert response.status_code == 502
    payload = response.get_json()
    assert payload["error"] == FAILED_JUEGO_MSG
    assert payload["errors"] == [["SteamSpider", "page structure changed"]]


def test_post_juego_partial_keeps_200_and_reports_errors(fake_trigger, client) -> None:
    FakeTriggerRunner.items = {"steam": {"nombre": "Half-Life"}, "gog": None, "egs": None}
    FakeTriggerRunner.errors = [("EpicgamesSpider", "xpath changed")]
    token = _csrf_token(client)
    response = _post_juego(client, "half-life", token)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["errors"] == [["EpicgamesSpider", "xpath changed"]]
    assert payload["steam"]["nombre"] == "Half-Life"


def test_post_juego_sanitizes_spider_payload(fake_trigger, client) -> None:
    FakeTriggerRunner.items = {
        "steam": {
            "nombre": "<script>alert(1)</script>",
            "descripcion": "<b>ok</b>",
            "link": "javascript:alert(1)",
            "img": "http://images.example/cover.jpg",
            "precio": 9.99,
        }
    }
    token = _csrf_token(client)
    response = _post_juego(client, "half-life", token)

    assert response.status_code == 200
    payload = response.get_json()["steam"]
    assert payload["link"] is None  # non-http(s) URI dropped
    assert payload["img"] == "http://images.example/cover.jpg"
    assert b"<script>" not in response.data


def test_post_ofertas_success(fake_trigger, client) -> None:
    FakeTriggerRunner.items = {"steam": [{"nombre": "Of1"}], "gog": [], "egs": []}
    token = _csrf_token(client)
    response = client.post("/ofertas", headers={"X-CSRFToken": token})

    assert response.status_code == 200
    assert response.get_json()["steam"] == [{"nombre": "Of1"}]
    (spiders, term, timeout), *_ = FakeTriggerRunner.launches
    assert spiders == tuple(OFFER_SPIDERS)
    assert term is None
    assert timeout == 60.0


def test_post_ofertas_timeout_maps_504(fake_trigger, client) -> None:
    FakeTriggerRunner.raise_exc = crochet.TimeoutError
    token = _csrf_token(client)
    response = client.post("/ofertas", headers={"X-CSRFToken": token})

    assert response.status_code == 504
    assert response.get_json()["error"] == TIMEOUT_OFERTAS_MSG


def test_post_ofertas_total_failure_maps_502(fake_trigger, client) -> None:
    FakeTriggerRunner.items = {}
    FakeTriggerRunner.errors = [("OffersSteamSpider", "boom")]
    token = _csrf_token(client)
    response = client.post("/ofertas", headers={"X-CSRFToken": token})

    assert response.status_code == 502
    payload = response.get_json()
    assert payload["error"] == FAILED_OFERTAS_MSG
    assert payload["errors"] == [["OffersSteamSpider", "boom"]]


def test_post_ofertas_all_stores_empty_without_errors_maps_502(
    fake_trigger, client
) -> None:
    """REQ-ASM-3 scenario 1: empty 200 {} must never reach the client."""
    FakeTriggerRunner.items = {"steam": [], "gog": [], "egs": []}
    token = _csrf_token(client)
    response = client.post("/ofertas", headers={"X-CSRFToken": token})

    assert response.status_code == 502
    payload = response.get_json()
    assert payload["error"] == FAILED_OFERTAS_MSG
    assert payload["errors"] == []


def test_post_juego_success_includes_currency(fake_trigger, client) -> None:
    """REQ-UI-7: 200 /juego envelope carries the configured currency."""
    FakeTriggerRunner.items = {"steam": {"nombre": "Half-Life"}, "gog": None, "egs": None}
    token = _csrf_token(client)
    response = _post_juego(client, "half-life", token)

    assert response.status_code == 200
    assert response.get_json()["currency"] == "USD"


def test_post_ofertas_success_includes_currency(fake_trigger, client) -> None:
    """REQ-UI-7: 200 /ofertas envelope carries the configured currency."""
    FakeTriggerRunner.items = {"steam": [{"nombre": "Of1"}], "gog": [], "egs": []}
    token = _csrf_token(client)
    response = client.post("/ofertas", headers={"X-CSRFToken": token})

    assert response.status_code == 200
    assert response.get_json()["currency"] == "USD"


def test_error_responses_omit_currency(fake_trigger, client) -> None:
    """REQ-UI-7: non-200 envelopes never include the currency key."""
    token = _csrf_token(client)

    bad_request = client.post("/juego", data={}, headers={"X-CSRFToken": token})
    assert bad_request.status_code == 400
    assert "currency" not in bad_request.get_json()

    FakeTriggerRunner.raise_exc = RuntimeError
    bad_gateway = _post_juego(client, "half-life", token)
    assert bad_gateway.status_code == 502
    assert "currency" not in bad_gateway.get_json()