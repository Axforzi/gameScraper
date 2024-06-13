import time

import sys
import os
sys.path.insert(1, os.getcwd())

import crochet
from scrapy import signals
from scrapy.crawler import CrawlerRunner, CrawlerProcess
from scrapy.signalmanager import dispatcher
from scrapy.utils.project import get_project_settings

from steamScrape.spiders.epicgames import EpicgamesSpider
from steamScrape.spiders.offers_egs import OffersEgsSpider

from steamScrape.spiders.gog import GogSpider
from steamScrape.spiders.offers_gog import OffersGogSpider

from steamScrape.spiders.steam import SteamSpider
from steamScrape.spiders.offers_steam import OffersSteamSpider

crochet.setup()
crawl_runner = CrawlerRunner(settings=get_project_settings())

class TriggerGame():
    def __init__(self):
        self.count = 0
        self.scrape_completed = False
        self.items = {}

    def parse_data(self, juego):
        self.scrape_with_crochet(juego=juego)

        while self.scrape_completed is False:
            time.sleep(2)

        return self.items

    def crawler_result(self, item):
        self.items.update(item)

    def finished_scrape(self, *args, **kwargs):
        self.count += 1
        if self.count == 3:
            self.scrape_completed = True

    @crochet.run_in_reactor
    def scrape_with_crochet(self, juego):
        dispatcher.connect(self.crawler_result, signal=signals.item_scraped)

        steamEventual = crawl_runner.crawl(SteamSpider, juego = juego)
        steamEventual.addCallback(self.finished_scrape)

        gogEventual = crawl_runner.crawl(GogSpider, juego = juego)
        gogEventual.addCallback(self.finished_scrape)

        epicEventual = crawl_runner.crawl(EpicgamesSpider, juego = juego)
        epicEventual.addCallback(self.finished_scrape)


class TriggerOffers():
    def __init__(self):
        self.count = 0
        self.scrape_completed = False
        self.items = {}

    def parse_data(self):
        self.scrape_with_crochet()

        while self.scrape_completed is False:
            time.sleep(2)

        return self.items

    def crawler_result(self, item):
        self.items.update(item)

    def finished_scrape(self, *args, **kwargs):
        self.count += 1
        if self.count == 3:
            self.scrape_completed = True

    @crochet.run_in_reactor
    def scrape_with_crochet(self):
        dispatcher.connect(self.crawler_result, signal=signals.item_scraped)

        steamEventual = crawl_runner.crawl(OffersSteamSpider)
        steamEventual.addCallback(self.finished_scrape)

        gogEventual = crawl_runner.crawl(OffersGogSpider)
        gogEventual.addCallback(self.finished_scrape)

        egsEventual = crawl_runner.crawl(OffersEgsSpider)
        egsEventual.addCallback(self.finished_scrape)