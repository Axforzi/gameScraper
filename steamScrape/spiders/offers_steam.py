"""Steam specials spider.

Malformed offers are logged and skipped instead of crashing the crawl
(REQ-TST-4).
"""

import logging

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


class OffersSteamSpider(scrapy.Spider):
    name = "offers_steam"

    # Same age-gate bypass as SteamSpider: without these cookies Steam serves
    # a verification page instead of the search results.
    cookiesConfig = {"birthtime": "1008392401", "lastagecheckage": "15-December-2001"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cfg = Settings.from_env(require_secret=False)
        self.headersConfig = {"Accept-Language": f"{cfg.locale},es;q=0.9"}
        self.start_urls = [
            "https://store.steampowered.com/search/?category1=998&os=win&specials=1&ndl=1"
        ]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                cookies=self.cookiesConfig,
                headers=self.headersConfig,
                callback=self.parse,
            )

    def parse(self, response):
        content = response.xpath("//div[@class='search_results']//a[@data-gpnav='item']")[0:9]

        for element in content:
            game = Juego()
            try:
                game["nombre"] = (element.css(".title::text").get() or "").strip()
                game["precio"] = _parse_price(
                    element.css(".discount_original_price::text").get()
                )
                game["descuento"] = _parse_price(
                    element.css(".discount_final_price::text").get()
                )
            except (TypeError, ValueError) as exc:
                logger.warning("malformed price store=steam_offers reason=%s", exc)
                continue
            game["link"] = element.css("::attr('href')").get()

            # GET IMG LINK (search-page thumbnail as fallback)
            game["img"] = element.css("img::attr('src')").get()

            # Follow each game page through the reactor to grab the full cover
            # instead of blocking with requests/BeautifulSoup.
            yield scrapy.Request(
                game["link"],
                callback=self.parse_offer,
                meta={"game": dict(game)},
                dont_filter=True,
                cookies=self.cookiesConfig,
                headers=self.headersConfig,
            )

    def parse_offer(self, response):
        game = response.meta["game"]
        cover = response.css("img.game_header_image_full::attr(src)").get()
        if cover:
            game["img"] = cover
        yield {"steam": [game]}