import scrapy
import json
from ..items import Juego

class OffersEgsSpider(scrapy.Spider):
    name = "offers_egs"
    start_urls = ["https://store.epicgames.com/graphql?operationName=searchStoreQuery&variables=%7B%22allowCountries%22:%22VE%22,%22category%22:%22games%2Fedition%2Fbase%22,%22comingSoon%22:false,%22count%22:40,%22country%22:%22VE%22,%22keywords%22:%22%22,%22locale%22:%22es-ES%22,%22sortBy%22:%22releaseDate%22,%22sortDir%22:%22DESC%22,%22start%22:0,%22tag%22:%2216011%22,%22withPrice%22:true%7D&extensions=%7B%22persistedQuery%22:%7B%22version%22:1,%22sha256Hash%22:%227d58e12d9dd8cb14c84a3ff18d360bf9f0caa96bf218f2c5fda68ba88d68a437%22%7D%7D"]

    def parse(self, response):
        data = json.loads(response.body)
        elements = data['data']['Catalog']['searchStore']['elements']

        games = []
        for i in range(10):
            game = Juego()
            game['nombre'] = elements[i]['title']
            game['precio'] = elements[i]['price']['totalPrice']['fmtPrice']['originalPrice']
            game['descuento'] = elements[i]['price']['totalPrice']['fmtPrice']['discountPrice']
            game['link'] = 'https://store.epicgames.com/es-ES/p/' + elements[i]['catalogNs']['mappings'][0]['pageSlug']
            game['img'] = elements[i]['keyImages'][2]['url']

            # CLEAN PRICES
            game['precio'] = float(game['precio'].replace('\xa0US$', '').replace(',', '.'))
            game['descuento'] = float(game['descuento'].replace('\xa0US$', '').replace(',', '.'))

            games.append(dict(game))

        yield {'egs': games}