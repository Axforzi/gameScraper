from typing import Any, Iterable
import scrapy
from ..items import Juego
import re

class SteamSpider(scrapy.Spider):
    name = "steam"

    cookiesConfig = {"birthtime": "1008392401", "lastagecheckage": "15-December-2001"}
    headersConfig = {"Accept-Language" : "es-ES,es;q=0.9"}

    def __init__(self, juego, *args, **kwargs: Any):
        super(SteamSpider).__init__(*args, **kwargs)
        self.juego = ' '.join(re.findall(r'[a-zA-Z0-9]+', juego))
        self.start_urls = [f'https://store.steampowered.com/search/?term={self.juego}&category1=998&os=win&hidef2p=1&ndl=1']

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, cookies=self.cookiesConfig, headers=self.headersConfig, callback=self.search_game)

    def search_game(self, response):
        url = response.css("#search_results #search_result_container a::attr('href')").get()
        released = response.xpath("//*[@id='search_result_container']//a[1]//*[@class='discount_final_price']").get()

        # VERIFY RESULTS AND IF GAME ITS RELEASED
        if (url != None) and (released != None):
            yield scrapy.Request(url,cookies=self.cookiesConfig, headers=self.headersConfig, callback=self.parse)
        else:
            yield {'steam': None}
    
    def parse(self, response):
        game = Juego()

        nombre = response.css('.apphub_AppName::text').get().strip()
        game['nombre'] = nombre.replace('®', '').replace('™', '')

        game['descripcion'] = response.css('.game_description_snippet::text').get().strip()
        game['link'] = response.request.url
        game['img'] = response.css('.game_header_image_full::attr(src)').get()

        # CHECK IF THERE'S A DISCOUNT
        game['precio'] = response.css('.game_area_purchase_game_wrapper .game_area_purchase_game .price::text').get()
        if game['precio'] == None:
            game['precio'] = response.css('.game_purchase_action .discount_original_price::text').get().strip()
            game['descuento'] = response.css('.game_purchase_action .discount_final_price::text').get().strip()

            #CLEAN PRICES
            game['precio'] = float(game['precio'].replace('$', ''))
            game['descuento'] = float(game['descuento'].replace('$', '').strip().split()[0])

            yield {'steam': dict(game)}
        else:
            game['precio'] = float(game['precio'].replace('$', '').strip().split()[0])
            game['descuento'] = None

            yield {'steam': dict(game)}
