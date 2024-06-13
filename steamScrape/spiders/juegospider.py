import scrapy
from ..items import Juego

class JuegoSpider(scrapy.Spider):
    name = "juego_spider"

    def __init__(self, link, *args, **kwargs):
        super(JuegoSpider).__init__(*args, **kwargs)
        self.start_urls = [link]

    def start_requests(self):
        cookiesConfig = {"birthtime": "1008392401", "lastagecheckage": "15-December-2001"}
        headersConfig = {"Accept-Language" : "es-ES,es;q=0.9"}
        
        for url in self.start_urls:
            yield scrapy.Request(url, headers=headersConfig, cookies=cookiesConfig)

    def parse(self, response):
        print('steam start scraping')
        game = Juego()
        game['nombre'] = response.css('.apphub_AppName::text').get().strip()
        game['descripcion'] = response.css('.game_description_snippet::text').get().strip()

        # CHECK IF THERE'S A DISCOUNT
        game['precio'] = response.css('.game_area_purchase_game .price::text').get()
        if game['precio'] == None:
            game['precio'] = response.css('.game_purchase_action .discount_original_price::text').get().strip()
            game['descuento'] = response.css('.game_purchase_action .discount_final_price::text').get().strip()
            game['descuento'] = float(game['descuento'].replace('$', '').strip().split()[0])
            yield {'steam': dict(game)}

        game['precio'] = float(game['precio'].replace('$', '').strip().split()[0])
        game['descuento'] = None

        print('steam end scraping')
        yield {'steam': dict(game)}
