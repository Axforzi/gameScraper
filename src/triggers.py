"""Crochet bridge between Flask trigger routes and Scrapy crawlers.

``TriggerRunner`` replaces the former ``TriggerGame``/``TriggerOffers`` split
(REQ-ASM-5): one class parameterized by the spider list, built on the Tier 1
timeout/cancel/error machinery. Completion is derived from the configured
spider list, never a hardcoded count.
"""

import logging
from typing import Any

import crochet
import scrapy
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import defer

crochet.setup()
crawl_runner = CrawlerRunner(settings=get_project_settings())

logger = logging.getLogger(__name__)

# Bounded budget to await the per-run stop before replying 504: the crawl has
# already blown the spider timeout, so a stuck stop must not tie the thread.
_CANCEL_WAIT_SECONDS = 5.0


class TriggerRunner:
    """Schedule one crawler per spider and block at most ``timeout`` seconds.

    State machine per run: PENDING -> RUNNING -> COMPLETED | PARTIAL | TIMEOUT
    | FAILED. Returns the merged items dict; raises ``crochet.TimeoutError``
    when the timeout elapses (after cancelling in-flight crawlers) and
    re-raises any pre-scheduling exception so the route can map it to an HTTP
    error. Instances are per-request; ``run()`` resets the per-run state.
    """

    def __init__(
        self,
        spiders: list[type[scrapy.Spider]],
        term: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.spiders = list(spiders)
        self.term = term
        self.timeout = timeout
        self.items: dict[str, Any] = {}
        self._errors: list[tuple[str, str]] = []
        self._crawlers: set[Any] = set()
        self._state = "PENDING"

    @property
    def state(self) -> str:
        return self._state

    @property
    def errors(self) -> list:
        return list(self._errors)

    def run(self) -> dict:
        self._state = "RUNNING"
        self._errors = []
        self.items = {}
        self._crawlers = set()
        eventual = self._schedule()
        try:
            eventual.wait(timeout=self.timeout)
        except crochet.TimeoutError:
            self._state = "TIMEOUT"
            self._stop_own_crawlers()
            names = ", ".join(spider.__name__ for spider in self.spiders)
            logger.warning("spider_timeout spider=%s timeout=%s", names, self.timeout)
            raise
        except Exception as exc:
            self._state = "FAILED"
            logger.exception("trigger failed before crawl finished: %s", exc)
            raise
        self._state = "PARTIAL" if self._errors else "COMPLETED"
        return self.items

    def _stop_own_crawlers(self) -> None:
        """Await the stop of THIS run's crawlers so no orphan keeps the reactor busy.

        The stop is awaited with a bounded budget: the spider timeout already
        elapsed, so a stuck stop must not delay the 504 response further.
        """
        try:
            self.cancel().wait(timeout=_CANCEL_WAIT_SECONDS)
        except Exception as exc:
            logger.warning("cancel did not complete cleanly: %s", exc)

    def cancel(self):
        """Stop and await only the crawlers created by this run.

        Runs asynchronously in the reactor thread and returns an
        ``EventualResult`` whose ``wait()`` blocks until every tracked
        crawler's ``stop()`` deferred has fired.
        """

        @crochet.run_in_reactor
        def _stop() -> Any:
            own_crawlers = tuple(self._crawlers)
            if not own_crawlers:
                return None
            return defer.DeferredList([crawler.stop() for crawler in own_crawlers])

        return _stop()

    @crochet.run_in_reactor
    def _schedule(self):
        for spider_cls in self.spiders:
            crawler = crawl_runner.create_crawler(spider_cls)
            self._crawlers.add(crawler)
            crawler.signals.connect(self._on_item, signal=signals.item_scraped)
            crawler.signals.connect(self._on_spider_error, signal=signals.spider_error)
            crawler.signals.connect(self._on_closed, signal=signals.spider_closed)
            kwargs = {"juego": self.term} if self.term is not None else {}
            deferred = crawl_runner.crawl(crawler, **kwargs)
            deferred.addErrback(self._on_crawl_error, spider_cls.__name__)
        return crawl_runner.join()

    def _on_item(self, item, response, spider):
        for key, value in dict(item).items():
            if key in self.items and isinstance(self.items[key], list) and isinstance(value, list):
                self.items[key].extend(value)
            else:
                self.items[key] = value

    def _on_spider_error(self, failure, response, spider):
        reason = failure.getErrorMessage() if failure else "unknown error"
        self._errors.append((spider.name, reason))
        logger.error("spider_error spider=%s reason=%s", spider.name, reason)

    def _on_crawl_error(self, failure, spider_name):
        reason = failure.getErrorMessage() if failure else "unknown error"
        self._errors.append((spider_name, reason))
        logger.error("trigger_error spider=%s reason=%s", spider_name, reason)

    def _on_closed(self, spider, reason):
        logger.debug("spider_closed spider=%s reason=%s", spider.name, reason)