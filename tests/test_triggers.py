"""TriggerRunner tests (REQ-TST-2, REQ-ASM-1/2/3 — threat-matrix RED cases).

Every crawler is faked; no live site is ever touched. The crochet reactor is
the single per-process one started by ``src.triggers`` import (conftest) —
tests that exercise the reactor bridge request the ``crochet_reactor``
fixture to make that dependency explicit.
"""

from __future__ import annotations

import types
from collections.abc import Callable

import crochet
import pytest
import scrapy
from scrapy import signals
from twisted.internet import defer

from src.triggers import TriggerRunner


class FakeSpider(scrapy.Spider):
    name = "fake"


class FailingSpider(scrapy.Spider):
    name = "fails"


class FakeEventual:
    """Stand-in for crochet's EventualResult with scripted wait behavior."""

    def __init__(self, behavior: str = "done", side_effect: Callable | None = None):
        self.behavior = behavior
        self.side_effect = side_effect
        self.timeout: float | None = None

    def wait(self, timeout: float | None = None) -> None:
        self.timeout = timeout
        if self.side_effect is not None:
            self.side_effect(self)
        if self.behavior == "timeout":
            raise crochet.TimeoutError()

    def cancel(self) -> None:
        pass


class FakeSignals:
    def __init__(self) -> None:
        self.connected: list[tuple[Callable, object]] = []

    def connect(self, callback: Callable, signal: object | None = None, **kwargs) -> None:
        self.connected.append((callback, signal))


class FakeCrawler:
    def __init__(
        self, spider_cls: type[scrapy.Spider], runner: FakeCrawlRunner | None = None
    ) -> None:
        self.spider_cls = spider_cls
        self.signals = FakeSignals()
        self.runner = runner
        self.stopped = False

    def stop(self):
        self.stopped = True
        if self.runner is not None:
            self.runner.stopped_crawlers.append(self)
        return defer.succeed(None)


class FakeDeferred:
    def __init__(self) -> None:
        self.errback_calls: list[tuple] = []

    def addErrback(self, fn: Callable, *args, **kwargs) -> None:
        self.errback_calls.append((fn, args, kwargs))


class FakeCrawlRunner:
    """Deterministic replacement for ``src.triggers.crawl_runner``."""

    def __init__(self) -> None:
        self.crawlers: list[FakeCrawler] = []
        self.stopped_crawlers: list[FakeCrawler] = []
        self.stopped = False
        self.last_crawl_kwargs: dict = {}

    def create_crawler(self, spider_cls: type[scrapy.Spider]) -> FakeCrawler:
        crawler = FakeCrawler(spider_cls, runner=self)
        self.crawlers.append(crawler)
        return crawler

    def crawl(self, crawler: FakeCrawler, **kwargs) -> FakeDeferred:
        self.last_crawl_kwargs = kwargs
        return FakeDeferred()

    def join(self) -> None:
        return None

    def stop(self) -> None:
        self.stopped = True


def _spider_with_errors() -> scrapy.Spider:
    spider = FakeSpider()
    spider.name = "fails"
    return spider


def test_initial_state() -> None:
    runner = TriggerRunner([FakeSpider], term="doom", timeout=5.0)
    assert runner.state == "PENDING"
    assert runner.errors == []
    assert runner.items == {}


def test_run_completes_within_timeout(monkeypatch) -> None:
    runner = TriggerRunner([FakeSpider], term="half-life", timeout=5.0)

    def fill(eventual: FakeEventual) -> None:
        runner.items["steam"] = [{"nombre": "Half-Life"}]

    monkeypatch.setattr(
        TriggerRunner, "_schedule", lambda self: FakeEventual(side_effect=fill)
    )
    result = runner.run()

    assert result == {"steam": [{"nombre": "Half-Life"}]}
    assert runner.state == "COMPLETED"
    assert runner.errors == []


def test_run_partial_preserves_successes(monkeypatch) -> None:
    runner = TriggerRunner([FakeSpider, FailingSpider], timeout=5.0)

    def fill(eventual: FakeEventual) -> None:
        runner.items["gog"] = [{"nombre": "Ok"}]
        runner._errors.append(("fails", "page structure changed"))

    monkeypatch.setattr(
        TriggerRunner, "_schedule", lambda self: FakeEventual(side_effect=fill)
    )
    result = runner.run()

    assert result == {"gog": [{"nombre": "Ok"}]}
    assert runner.state == "PARTIAL"
    assert runner.errors == [("fails", "page structure changed")]


def test_run_timeout_aborts_and_cancels(crochet_reactor, monkeypatch) -> None:
    fake_runner = FakeCrawlRunner()
    monkeypatch.setattr("src.triggers.crawl_runner", fake_runner)
    runner = TriggerRunner([FakeSpider], timeout=0.1)

    eventual = FakeEventual(behavior="timeout")
    monkeypatch.setattr(TriggerRunner, "_schedule", lambda self: eventual)

    cancel_calls: list[TriggerRunner] = []
    real_cancel = TriggerRunner.cancel

    def spy_cancel(self) -> object:
        cancel_calls.append(self)
        result = real_cancel(self)
        result.wait(timeout=5)  # deterministic: reactor executed stop()
        return result

    monkeypatch.setattr(TriggerRunner, "cancel", spy_cancel)

    with pytest.raises(crochet.TimeoutError):
        runner.run()

    assert runner.state == "TIMEOUT"
    assert eventual.timeout == 0.1  # configured timeout reached the wait
    assert cancel_calls == [runner]
    assert fake_runner.stopped is False  # global runner stop no longer used
    assert fake_runner.stopped_crawlers == []  # no crawlers were scheduled


def test_run_failed_on_exception_during_wait(monkeypatch) -> None:
    """The decorated ``_schedule`` surfaces reactor errors via ``wait()``."""

    runner = TriggerRunner([FakeSpider], timeout=5.0)

    def boom(eventual: FakeEventual) -> None:
        raise RuntimeError("reactor unavailable")

    monkeypatch.setattr(
        TriggerRunner, "_schedule", lambda self: FakeEventual(side_effect=boom)
    )

    with pytest.raises(RuntimeError, match="reactor unavailable"):
        runner.run()

    assert runner.state == "FAILED"


def test_state_is_running_during_wait(monkeypatch) -> None:
    runner = TriggerRunner([FakeSpider], timeout=5.0)
    states_seen: list[str] = []

    def observe(eventual: FakeEventual) -> None:
        states_seen.append(runner.state)

    monkeypatch.setattr(
        TriggerRunner, "_schedule", lambda self: FakeEventual(side_effect=observe)
    )
    runner.run()

    assert "RUNNING" in states_seen
    assert runner.state == "COMPLETED"


def test_run_resets_state_between_requests(monkeypatch) -> None:
    runner = TriggerRunner([FakeSpider], timeout=5.0)
    runner._state = "FAILED"
    runner._errors = [("fake", "stale")]

    monkeypatch.setattr(TriggerRunner, "_schedule", lambda self: FakeEventual())
    runner.run()

    assert runner.state == "COMPLETED"
    assert runner.errors == []


def test_cancel_stops_only_own_crawlers(crochet_reactor, monkeypatch) -> None:
    """Timeout cancellation must not stop another request's in-flight crawlers."""
    fake_runner = FakeCrawlRunner()
    monkeypatch.setattr("src.triggers.crawl_runner", fake_runner)

    runner_a = TriggerRunner([FakeSpider])
    runner_b = TriggerRunner([FakeSpider])

    # Both runs "schedule" one crawler each; only A's should be stopped.
    crawler_a = fake_runner.create_crawler(FakeSpider)
    crawler_b = fake_runner.create_crawler(FakeSpider)
    runner_a._crawlers.add(crawler_a)
    runner_b._crawlers.add(crawler_b)

    eventual = runner_a.cancel()
    eventual.wait(timeout=5)

    assert crawler_a in fake_runner.stopped_crawlers
    assert crawler_b not in fake_runner.stopped_crawlers
    assert crawler_b.stopped is False
    assert fake_runner.stopped is False  # shared runner stop never invoked


def test_schedule_wires_per_crawler_signals(crochet_reactor, monkeypatch) -> None:
    fake_runner = FakeCrawlRunner()
    monkeypatch.setattr("src.triggers.crawl_runner", fake_runner)

    runner = TriggerRunner([FakeSpider], term="doom")
    eventual = runner._schedule()
    eventual.wait(timeout=5)

    (crawler,) = fake_runner.crawlers
    connected_signals = {signal for _, signal in crawler.signals.connected}
    assert connected_signals == {signals.item_scraped, signals.spider_error, signals.spider_closed}
    assert fake_runner.last_crawl_kwargs == {"juego": "doom"}
    assert set(runner._crawlers) == {crawler}  # per-run tracking for cancel


def test_schedule_omits_term_kwarg_when_none(crochet_reactor, monkeypatch) -> None:
    fake_runner = FakeCrawlRunner()
    monkeypatch.setattr("src.triggers.crawl_runner", fake_runner)

    runner = TriggerRunner([FakeSpider])
    eventual = runner._schedule()
    eventual.wait(timeout=5)

    assert fake_runner.last_crawl_kwargs == {}


def test_on_item_merges_store_lists() -> None:
    runner = TriggerRunner([FakeSpider])
    spider = FakeSpider()

    runner._on_item({"steam": [{"nombre": "A"}]}, None, spider)
    runner._on_item({"steam": [{"nombre": "B"}]}, None, spider)

    assert runner.items == {"steam": [{"nombre": "A"}, {"nombre": "B"}]}


def test_on_item_replaces_non_list_value() -> None:
    runner = TriggerRunner([FakeSpider])
    spider = FakeSpider()

    runner._on_item({"steam": {"nombre": "A"}}, None, spider)
    runner._on_item({"gog": [{"nombre": "B"}]}, None, spider)
    runner._on_item({"steam": {"nombre": "C"}}, None, spider)

    assert runner.items == {"steam": {"nombre": "C"}, "gog": [{"nombre": "B"}]}


def test_on_spider_error_records_name_and_reason() -> None:
    runner = TriggerRunner([FakeSpider])
    failure = types.SimpleNamespace(getErrorMessage=lambda: "boom")
    spider = _spider_with_errors()

    runner._on_spider_error(failure, None, spider)

    assert runner.errors == [("fails", "boom")]


def test_on_crawl_error_records_name_and_reason() -> None:
    runner = TriggerRunner([FakeSpider])
    failure = types.SimpleNamespace(getErrorMessage=lambda: "crawl exploded")

    runner._on_crawl_error(failure, "fails")

    assert runner.errors == [("fails", "crawl exploded")]