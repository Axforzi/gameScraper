"""Daily offers cache backed by an atomic JSON file.

On startup a daemon thread fetches all offer spiders once, builds the
sanitized envelope (currency + errors), and writes it to ``offers_cache_path``
using an atomic write (tmp → os.replace).  Every ``interval`` seconds the
file is overwritten with fresh data.

Routes read the file on every POST /ofertas request, so the live crawl is
never triggered from the web layer.
"""

from __future__ import annotations

import json
import logging
import tempfile
import threading
import time
from pathlib import Path

import crochet

from src.routes.index import (
    _sanitize_payload,
    _sanitize_text,
)
from src.triggers import TriggerRunner
from steamScrape.spiders.offers_egs import OffersEgsSpider
from steamScrape.spiders.offers_gog import OffersGogSpider
from steamScrape.spiders.offers_steam import OffersSteamSpider

logger = logging.getLogger(__name__)

_DEFAULT_SPIDERS = [OffersSteamSpider, OffersGogSpider, OffersEgsSpider]


class OffersCache:
    """Singleton-ish background cache that refreshes offer data periodically.

    Parameters
    ----------
    path:
        Filesystem path for the JSON cache file.
    currency:
        Currency code embedded in the envelope (e.g. ``"USD"``).
    spider_timeout:
        Maximum seconds to wait for the crawl to finish.
    interval:
        Seconds between refreshes (default 86 400 = 24 h).
    spiders:
        List of spider classes to crawl.  Defaults to all three offer spiders.
    trigger_runner:
        Callable ``(spiders, term, timeout) -> TriggerRunner``.  Injectable
        for testing; production uses the real ``TriggerRunner``.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        currency: str,
        spider_timeout: float = 60.0,
        interval: float = 86400.0,
        spiders: list | None = None,
        trigger_runner=None,
    ) -> None:
        self.path = Path(path)
        self.currency = currency
        self.spider_timeout = spider_timeout
        self.interval = interval
        self.spiders = spiders or list(_DEFAULT_SPIDERS)
        self._runner_cls = trigger_runner or TriggerRunner
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> dict | None:
        """Return the cached payload dict, or *None* if unavailable / corrupt."""
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def refresh(self) -> dict | None:
        """Run the crawl, build the sanitized envelope, and write it atomically.

        On failure the existing file is **never** overwritten — callers always
        fall back to the last good snapshot.
        """
        try:
            scrape = self._runner_cls(
                self.spiders, timeout=self.spider_timeout
            )
            result = scrape.run()
        except crochet.TimeoutError:
            logger.warning("offers cache refresh timed out")
            return None
        except Exception:
            logger.exception("offers cache refresh failed")
            return None

        payload = dict(result)
        payload["currency"] = self.currency
        if scrape.errors:
            payload["errors"] = [
                [name, _sanitize_text(reason)] for name, reason in scrape.errors
            ]
        sanitized = _sanitize_payload(payload)

        # Atomic write: tmp file in the same directory → os.replace.
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                dir=self.path.parent, suffix=".tmp", prefix=".offers-"
            )
            try:
                with open(fd, "w", encoding="utf-8") as fh:
                    json.dump(sanitized, fh, ensure_ascii=False)
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
            import os
            os.replace(tmp, self.path)
        except OSError:
            logger.exception("failed to write offers cache file %s", self.path)
            return None

        return sanitized

    def start(self) -> None:
        """Launch the daemon refresh loop in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._loop, name="offers-cache", daemon=True
        )
        self._thread.start()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while True:
            try:
                self.refresh()
            except Exception:
                logger.exception("offers-cache loop iteration failed")
            time.sleep(self.interval)


def start_offers_cache(settings) -> OffersCache:
    """Build an ``OffersCache`` from *settings*, start it, and return it."""
    cache = OffersCache(
        settings.offers_cache_path,
        currency=settings.currency,
        spider_timeout=settings.spider_timeout,
        interval=settings.offers_cache_interval,
    )
    cache.start()
    return cache
