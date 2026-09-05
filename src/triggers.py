import logging
import os
import sys

sys.path.insert(1, os.getcwd())

import crochet
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings

from steamScrape.spiders.epicgames import EpicgamesSpider
from steamScrape.spiders.gog import GogSpider
from steamScrape.spiders.offers_egs import OffersEgsSpider
from steamScrape.spiders.offers_gog import OffersGogSpider
from steamScrape.spiders.offers_steam import OffersSteamSpider
from steamScrape.spiders.steam import SteamSpider

crochet.setup()
crawl_runner = CrawlerRunner(settings=get_project_settings())

logger = logging.getLogger(__name__)


class _TriggerBase:
    """Shared Crochet bridge: schedules one crawler per spider and waits with a timeout.

    State machine per run: PENDING → RUNNING → COMPLETED | PARTIAL | TIMEOUT | FAILED.
    """

    spiders = []

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self.items = {}
        self._errors = []
        self._state = "PENDING"

    @property
    def state(self) -> str:
        return self._state

    @property
    def errors(self) -> list:
        return list(self._errors)

    def run(self, term=None) -> dict:
        """Schedule all spiders and block at most ``timeout`` seconds.

        Returns the merged items dict. Raises ``crochet.TimeoutError`` when the
        timeout elapses (after cancelling in-flight crawlers) and re-raises any
        pre-scheduling exception so the route can map it to an HTTP error.
        """
        self._state = "RUNNING"
        self._errors = []
        self.items = {}
        eventual = self._schedule(term)
        try:
            eventual.wait(timeout=self.timeout)
        except crochet.TimeoutError:
            self.cancel()
            self._state = "TIMEOUT"
            names = ", ".join(spider.__name__ for spider in self.spiders)
            logger.warning("spider_timeout spider=%s timeout=%s", names, self.timeout)
            raise
        except Exception as exc:
            self._state = "FAILED"
            logger.exception("trigger failed before crawl finished: %s", exc)
            raise
        self._state = "PARTIAL" if self._errors else "COMPLETED"
        return self.items

    def cancel(self):
        """Stop every tracked crawler so no orphan keeps the reactor busy.

        Runs asynchronously in the reactor thread; the returned
        ``EventualResult`` can be awaited when callers need to know the stop
        completed.
        """

        @crochet.run_in_reactor
        def _stop() -> None:
            crawl_runner.stop()

        return _stop()

    @crochet.run_in_reactor
    def _schedule(self, term):
        for spider_cls in self.spiders:
            crawler = crawl_runner.create_crawler(spider_cls)
            crawler.signals.connect(self._on_item, signal=signals.item_scraped)
            crawler.signals.connect(self._on_spider_error, signal=signals.spider_error)
            crawler.signals.connect(self._on_closed, signal=signals.spider_closed)
            kwargs = {"juego": term} if term is not None else {}
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


class TriggerGame(_TriggerBase):
    def __init__(self, timeout: float = 60.0):
        super().__init__(timeout)
        self.spiders = [SteamSpider, GogSpider, EpicgamesSpider]

    def parse_data(self, juego):
        return self.run(juego)


class TriggerOffers(_TriggerBase):
    def __init__(self, timeout: float = 60.0):
        super().__init__(timeout)
        self.spiders = [OffersSteamSpider, OffersGogSpider, OffersEgsSpider]

    def parse_data(self):
        return self.run()