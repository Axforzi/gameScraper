"""Steam search + game page spider.

Malformed or missing prices are logged and yield ``{'steam': None}`` instead
of crashing the crawl (REQ-TST-4).
"""

import logging
import re

import scrapy

from src.config import Settings

from ..items import Juego

logger = logging.getLogger(__name__)


def _parse_price(value: str | None) -> float:
    """Convert a store price string (``$19.99``) to float."""
    cleaned = (value or "").replace("$", "").strip()
    if not cleaned:
        raise ValueError("empty price")
    return float(cleaned.split()[0])


class SteamSpider(scrapy.Spider):
    name = "steam"

    cookiesConfig = {"birthtime": "1008392401", "lastagecheckage": "15-December-2001"}

    def __init__(self, juego, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cfg = Settings.from_env(require_secret=False)
        self.juego = " ".join(re.findall(r"[a-zA-Z0-9]+", juego))
        self.headersConfig = {"Accept-Language": f"{cfg.locale},es;q=0.9"}
        self.start_urls = [
            "https://store.steampowered.com/search/"
            f"?term={self.juego}&category1=998&os=win&hidef2p=1&ndl=1"
        ]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                cookies=self.cookiesConfig,
                headers=self.headersConfig,
                callback=self.search_game,
            )

    def search_game(self, response):
        url = response.css(
            "#search_results #search_result_container a::attr('href')"
        ).get()
        released = response.xpath(
            "//*[@id='search_result_container']//a[1]//*[@class='discount_final_price']"
        ).get()

        # VERIFY RESULTS AND IF GAME ITS RELEASED
        if url is not None and released is not None:
            yield scrapy.Request(
                url,
                cookies=self.cookiesConfig,
                headers=self.headersConfig,
                callback=self.parse,
            )
        else:
            yield {"steam": None}

    def parse(self, response):
        game = Juego()

        nombre = response.css(".apphub_AppName::text").get()
        game["nombre"] = (nombre or "").strip().replace("®", "").replace("™", "")

        descripcion = response.css(".game_description_snippet::text").get()
        game["descripcion"] = (descripcion or "").strip()
        game["link"] = response.request.url
        game["img"] = response.css(".game_header_image_full::attr(src)").get()

        # CHECK IF THERE'S A DISCOUNT
        precio = response.css(
            ".game_area_purchase_game_wrapper .game_area_purchase_game .price::text"
        ).get()
        if precio is None:
            precio = response.css(
                ".game_purchase_action .discount_original_price::text"
            ).get()
            descuento = response.css(
                ".game_purchase_action .discount_final_price::text"
            ).get()
            try:
                game["precio"] = _parse_price(precio)
                game["descuento"] = _parse_price(descuento)
            except (TypeError, ValueError) as exc:
                logger.warning("malformed price store=steam reason=%s", exc)
                yield {"steam": None}
                return
        else:
            try:
                game["precio"] = _parse_price(precio)
            except (TypeError, ValueError) as exc:
                logger.warning("malformed price store=steam reason=%s", exc)
                yield {"steam": None}
                return
            game["descuento"] = None

        yield {"steam": dict(game)}