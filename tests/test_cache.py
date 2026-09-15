"""Tests for the daily offers cache (src/cache)."""

from __future__ import annotations

import json

import crochet

from src.cache import OffersCache


class FakeRunner:
    """Minimal stand-in that avoids the Crochet reactor."""

    def __init__(self, spiders, term=None, timeout=None):
        self.spiders = spiders
        self.term = term
        self.timeout = timeout
        self._items: dict = {
            "steam": [{"nombre": "Of1"}],
            "gog": [],
            "egs": [],
        }
        self.errors: list = []

    def run(self) -> dict:
        return dict(self._items)


class _RaisingRunner(FakeRunner):
    """Runner whose run() raises a given exception class (set via class var)."""

    _exc_cls: type[Exception] | None = None

    def run(self):
        if self._exc_cls is not None:
            raise self._exc_cls()
        return super().run()


class _WorkingRunner(FakeRunner):
    def run(self):
        return super().run()


# ── tests ──────────────────────────────────────────────────────────────


def test_load_returns_none_when_missing(tmp_path):
    cache = OffersCache(
        tmp_path / "offers.json", currency="USD", trigger_runner=_WorkingRunner
    )
    assert cache.load() is None


def test_load_returns_none_on_corrupt(tmp_path):
    path = tmp_path / "offers.json"
    path.write_text("{invalid json", encoding="utf-8")
    cache = OffersCache(path, currency="USD", trigger_runner=_WorkingRunner)
    assert cache.load() is None


def test_refresh_writes_sanitized_envelope_with_currency(tmp_path):
    cache = OffersCache(
        tmp_path / "offers.json",
        currency="USD",
        trigger_runner=_WorkingRunner,
    )
    result = cache.refresh()

    assert result is not None
    assert result["currency"] == "USD"
    assert result["steam"] == [{"nombre": "Of1"}]
    assert cache.path.exists()

    # Round-trip: load back and verify currency survives.
    loaded = cache.load()
    assert loaded is not None
    assert loaded["currency"] == "USD"
    assert loaded["steam"] == [{"nombre": "Of1"}]


def test_refresh_sanitizes_text_fields(tmp_path):
    class _SanitizingRunner(_WorkingRunner):
        def run(self):
            self._items = {
                "steam": [
                    {
                        "nombre": "<script>alert(1)</script>",
                        "link": "javascript:evil()",
                        "img": "http://ok.example/img.jpg",
                    }
                ],
                "gog": [],
                "egs": [],
            }
            return super().run()

    cache = OffersCache(
        tmp_path / "offers.json",
        currency="USD",
        trigger_runner=_SanitizingRunner,
    )
    result = cache.refresh()
    assert result is not None
    item = result["steam"][0]
    assert "<script>" not in item["nombre"]
    assert item["link"] is None  # javascript: URI dropped
    assert item["img"] == "http://ok.example/img.jpg"


def test_refresh_never_overwrites_existing_file_on_failure(tmp_path):
    path = tmp_path / "offers.json"
    existing = {"steam": [{"nombre": "old"}], "currency": "EUR"}
    path.write_text(json.dumps(existing), encoding="utf-8")

    _RaisingRunner._exc_cls = crochet.TimeoutError
    cache = OffersCache(
        path, currency="USD", trigger_runner=_RaisingRunner
    )
    result = cache.refresh()

    assert result is None
    # File content must be unchanged.
    assert json.loads(path.read_text(encoding="utf-8")) == existing
    _RaisingRunner._exc_cls = None


def test_refresh_never_overwrites_on_generic_exception(tmp_path):
    path = tmp_path / "offers.json"
    existing = {"steam": [{"nombre": "old"}], "currency": "GBP"}
    path.write_text(json.dumps(existing), encoding="utf-8")

    _RaisingRunner._exc_cls = RuntimeError
    cache = OffersCache(
        path, currency="USD", trigger_runner=_RaisingRunner
    )
    result = cache.refresh()

    assert result is None
    assert json.loads(path.read_text(encoding="utf-8")) == existing
    _RaisingRunner._exc_cls = None


def test_refresh_includes_errors(tmp_path):
    class _ErrorRunner(_WorkingRunner):
        def run(self):
            self.errors = [("OffersSteamSpider", "timeout")]
            return {"steam": [], "gog": [{"nombre": "G1"}], "egs": []}

    cache = OffersCache(
        tmp_path / "offers.json",
        currency="USD",
        trigger_runner=_ErrorRunner,
    )
    result = cache.refresh()
    assert result is not None
    assert result["errors"] == [["OffersSteamSpider", "timeout"]]


def test_offers_cache_starts_daemon_thread(tmp_path):
    cache = OffersCache(
        tmp_path / "offers.json",
        currency="USD",
        interval=99999,  # very long so the loop sleeps
        trigger_runner=_WorkingRunner,
    )
    cache.start()

    assert cache._thread is not None
    assert cache._thread.is_alive()
    assert cache._thread.daemon is True
    assert cache._thread.name == "offers-cache"

    # Clean shutdown: thread is daemon so it dies with the process, but for
    # test hygiene we join with a short timeout.
    cache._thread.join(timeout=2)


def test_start_is_idempotent(tmp_path):
    cache = OffersCache(
        tmp_path / "offers.json",
        currency="USD",
        interval=99999,
        trigger_runner=_WorkingRunner,
    )
    cache.start()
    first = cache._thread
    cache.start()  # should be a no-op
    assert cache._thread is first

    first.join(timeout=2)
