import scrapy
import json
from ..items import Juego

class OffersGogSpider(scrapy.Spider):
    name = "offers_gog"
    start_urls = ["https://catalog.gog.com/v1/catalog?limit=48&order=desc%3Atrending&discounted=eq%3Atrue&productType=in%3Agame%2Cpack%2Cdlc%2Cextras&page=1&countryCode=US&locale=en-US&currencyCode=USD"]

    def parse(self, response):
        data = json.loads(response.body)['products']

        games = []
        for i in range(10):
            game = Juego()
            game['nombre'] = data[i]['title']
            game['precio'] = float(data[i]['price']['base'].replace('$', ''))
            game['descuento'] = float(data[i]['price']['final'].replace('$', ''))
            game['link'] = data[i]['storeLink']
            game['img'] = data[i]['coverVertical']
            games.append(dict(game))

        yield {'gog': games}
            