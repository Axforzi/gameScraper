import scrapy
import json
from ..items import Juego

class OffersEgsSpider(scrapy.Spider):
    name = "offers_egs"
    start_urls = ['https://store.epicgames.com/graphql?operationName=searchStoreQuery&variables=%7B"allowCountries":"VE","category":"games%2Fedition%2Fbase","count":40,"country":"VE","effectiveDate":"[,2025-05-06T16:17:10.991Z]","keywords":"","locale":"es-ES","onSale":true,"sortBy":"relevancy,viewableDate","sortDir":"DESC,DESC","start":0,"tag":"9547","withPrice":true%7D&extensions=%7B"persistedQuery":%7B"version":1,"sha256Hash":"7d58e12d9dd8cb14c84a3ff18d360bf9f0caa96bf218f2c5fda68ba88d68a437"%7D%7D']

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