"""Epic Games Store specials spider (top-10 on-sale elements).

Malformed elements are logged and skipped instead of crashing the crawl
(REQ-TST-4).
"""

import json
import logging

import scrapy

from src.config import Settings

from ..items import Juego

logger = logging.getLogger(__name__)


class OffersEgsSpider(scrapy.Spider):
    name = "offers_egs"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cfg = Settings.from_env(require_secret=False)
        self.locale = cfg.locale
        self.start_urls = [
            f'https://store.epicgames.com/graphql?operationName=searchStoreQuery&variables=%7B"allowCountries":"{cfg.country}","category":"games%2Fedition%2Fbase","count":40,"country":"{cfg.country}","effectiveDate":"[,2025-05-06T16:17:10.991Z]","keywords":"","locale":"{cfg.locale}","onSale":true,"sortBy":"relevancy,viewableDate","sortDir":"DESC,DESC","start":0,"tag":"9547","withPrice":true%7D&extensions=%7B"persistedQuery":%7B"version":1,"sha256Hash":"7d58e12d9dd8cb14c84a3ff18d360bf9f0caa96bf218f2c5fda68ba88d68a437"%7D%7D'
        ]

    def parse(self, response):
        data = json.loads(response.body)
        elements = data["data"]["Catalog"]["searchStore"]["elements"]

        games = []
        for element in elements[:10]:
            game = Juego()
            try:
                game["nombre"] = element["title"]
                game["precio"] = float(
                    element["price"]["totalPrice"]["fmtPrice"]["originalPrice"]
                    .replace("\xa0US$", "")
                    .replace(",", ".")
                )
                game["descuento"] = float(
                    element["price"]["totalPrice"]["fmtPrice"]["discountPrice"]
                    .replace("\xa0US$", "")
                    .replace(",", ".")
                )
                game["link"] = (
                    f"https://store.epicgames.com/{self.locale}/p/"
                    + element["catalogNs"]["mappings"][0]["pageSlug"]
                )
                game["img"] = element["keyImages"][2]["url"]
            except (TypeError, ValueError, KeyError, IndexError) as exc:
                logger.warning("malformed product store=egs_offers reason=%s", exc)
                continue
            games.append(dict(game))

        yield {"egs": games}