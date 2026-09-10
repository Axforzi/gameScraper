"""GOG catalog search spider.

Malformed products are logged and skipped instead of crashing the crawl
(REQ-TST-4). ``parse`` returns the first matching product as a follow-up
``scrapy.Request``; ``{'gog': None}`` when nothing matches.
"""

import json
import logging
import re

import roman
import scrapy

from src.config import Settings

from ..items import Juego

logger = logging.getLogger(__name__)


class GogSpider(scrapy.Spider):
    name = "gog"

    def __init__(self, juego, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cfg = Settings.from_env(require_secret=False)
        self.juego = " ".join(re.findall(r"[a-zA-Z0-9]+", juego))
        self.start_urls = [
            "https://catalog.gog.com/v1/catalog"
            f"?limit=48&query=like%3A{self.juego}&order=asc%3Atitle"
            "&productType=in%3Agame%2Cpack%2C&page=1"
            f"&countryCode={cfg.gog_country}&locale={cfg.gog_locale}"
            f"&currencyCode={cfg.gog_currency}"
        ]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        game = Juego()
        data = json.loads(response.body)

        for product in data["products"]:
            try:
                result = self._match_product(product, game)
            except (TypeError, ValueError, KeyError) as exc:
                logger.warning("malformed product store=gog reason=%s", exc)
                continue
            if result is not None:
                return result

        return {"gog": None}

    def _match_product(self, product, game):
        """Build the candidate game; return a Request when it matches the term."""

        # Products without a price (null in the GOG catalog API) are skipped
        # silently instead of crashing the crawl (malformed-product handling).
        if not product.get("price") or not product.get("title"):
            return None

        # NAME OPERATIONS
        modiNombre = " ".join(re.findall(r"[a-zA-Z0-9]+", product["title"]))
        modiNombre = "".join(
            x if len(x) == 1 else f" {x}" for x in modiNombre.split()
        ).strip()
        game["nombre"] = product["title"]

        game["precio"] = float(product["price"]["base"].replace("$", ""))
        game["descuento"] = float(product["price"]["final"].replace("$", ""))
        game["link"] = product["storeLink"]
        game["img"] = product["coverVertical"]
        if game["precio"] == game["descuento"]:
            game["descuento"] = None

        # CHECK NAME NUMBER
        if re.search(r"[0-9]+", self.juego):
            numberFound = re.finditer(r"[0-9]+", self.juego)
            nameConverted = [
                self.juego[0 : m.start()]
                + roman.toRoman(int(self.juego[m.start() : m.end()]))
                + self.juego[m.end() : -1]
                for m in numberFound
            ][0]

            if (game["precio"] != 0) and (
                re.search(rf".*{self.juego.lower()}.*", modiNombre.lower())
                or re.search(rf".*{nameConverted.lower()}.*", modiNombre.lower())
            ):
                return scrapy.Request(
                    url=game["link"],
                    callback=self.get_description,
                    cb_kwargs={"game": game},
                )
        else:
            if (game["precio"] != 0) and (
                re.search(rf".*{self.juego.lower()}.*", modiNombre.lower())
            ):
                return scrapy.Request(
                    url=game["link"],
                    callback=self.get_description,
                    cb_kwargs={"game": game},
                )
        return None

    def get_description(self, response, game):
        descriptionList = response.css(".description::text").getall()
        description = ""
        for p in descriptionList:
            description += p.strip()
        game["descripcion"] = description
        return {"gog": dict(game)}