"""GOG specials spider (top-10 discounted products).

Malformed products are logged and skipped instead of crashing the crawl
(REQ-TST-4).
"""

import json
import logging

import scrapy

from src.config import Settings

from ..items import Juego

logger = logging.getLogger(__name__)


class OffersGogSpider(scrapy.Spider):
    name = "offers_gog"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cfg = Settings.from_env(require_secret=False)
        self.start_urls = [
            "https://catalog.gog.com/v1/catalog"
            "?limit=48&order=desc%3Atrending&discounted=eq%3Atrue"
            "&productType=in%3Agame%2Cpack%2Cdlc%2Cextras&page=1"
            f"&countryCode={cfg.gog_country}&locale={cfg.gog_locale}"
            f"&currencyCode={cfg.gog_currency}"
        ]

    def parse(self, response):
        data = json.loads(response.body)["products"]

        games = []
        for product in data[:9]:
            game = Juego()
            try:
                game["nombre"] = product["title"]
                game["precio"] = float(product["price"]["base"].replace("$", ""))
                game["descuento"] = float(product["price"]["final"].replace("$", ""))
                game["link"] = product["storeLink"]
                game["img"] = product["coverVertical"]
            except (TypeError, ValueError, KeyError) as exc:
                logger.warning("malformed product store=gog_offers reason=%s", exc)
                continue
            games.append(dict(game))

        yield {"gog": games}