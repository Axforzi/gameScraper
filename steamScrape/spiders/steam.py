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
    """Convert a store price string (``$19.99``, ``19,99 EUR``) to float.

    Whitespace-only or non-numeric values raise ``ValueError`` so the caller
    logs a malformed-price warning and skips the item (REQ-TST-4). The regex
    extraction tolerates trailing currency suffixes and locale decimal commas.
    """
    cleaned = (value or "").strip().replace("\xa0", " ")
    if not cleaned:
        raise ValueError("empty price")
    match = re.search(r"\d+(?:[.,]\d+)?", cleaned)
    if not match:
        raise ValueError("empty price")
    return float(match.group(0).replace(",", "."))


def _price_from_cents(value: str | None) -> float:
    """Convert Steam's ``data-price-*`` cents attribute (``"4499"``) to float.

    Steam serves these attributes on modern page markup even when the price
    text lives inside a child node, so prefer them over ``::text``.
    """
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError("empty price")
    try:
        return float(cleaned) / 100
    except ValueError as exc:
        raise ValueError("empty price") from exc


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

    def _initial_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                cookies=self.cookiesConfig,
                headers=self.headersConfig,
                callback=self.search_game,
            )

    async def start(self):
        # Scrapy >= 2.13 calls the async ``start()`` generator instead of the
        # legacy sync ``start_requests()``; without this override the engine
        # falls back to the base Spider.start(), which schedules start_urls
        # with the default ``parse`` callback and the search page never reaches
        # ``search_game``.
        for request in self._initial_requests():
            yield request

    def start_requests(self):
        # Kept for Scrapy < 2.13 compatibility and direct-call tests.
        yield from self._initial_requests()

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

        # CHECK IF THERE'S A DISCOUNT.
        # Steam's 2025+ markup puts the price in a child node (often a span),
        # so ``.price::text`` can match whitespace only. The ``data-price-final``
        # / ``data-price-original`` cents attributes are the stable signal:
        # prefer them, fall back to the text node.
        wrapper = ".game_area_purchase_game_wrapper .game_area_purchase_game"
        price_el = response.css(f"{wrapper} .price")
        precio_cents = price_el.css("::attr(data-price-final)").get()
        precio_text = price_el.css("::text").get()

        if precio_cents is not None:
            try:
                game["precio"] = _price_from_cents(precio_cents)
            except (TypeError, ValueError) as exc:
                logger.warning("malformed price store=steam reason=%s", exc)
                yield {"steam": None}
                return
            game["descuento"] = None
        elif precio_text is not None:
            try:
                game["precio"] = _parse_price(precio_text)
            except (TypeError, ValueError) as exc:
                logger.warning("malformed price store=steam reason=%s", exc)
                yield {"steam": None}
                return
            game["descuento"] = None
        else:
            precio = response.css(
                ".game_purchase_action .discount_original_price::attr(data-price-original)"
            ).get()
            descuento = response.css(
                ".game_purchase_action .discount_final_price::attr(data-price-final)"
            ).get()
            if precio is None or descuento is None:
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

        yield {"steam": dict(game)}