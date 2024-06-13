import scrapy
from scrapy.utils.log import configure_logging
from ..items import Juego
import json
import re
import roman

#configure_logging({"LOG_FORMAT": "%(levelname)s: %(message)s"})

class EpicgamesSpider(scrapy.Spider):
    name = "epicgames"
    juego = ''

    def __init__(self, juego, *args, **kwargs):
        super(EpicgamesSpider).__init__(*args, **kwargs)
        self.juego = ' '.join(re.findall(r'[a-zA-Z0-9]+', juego))
        url = f"https://store.epicgames.com/graphql?operationName=searchStoreQuery&variables=%7B%22allowCountries%22:%22VE%22,%22category%22:%22games%2Fedition%2Fbase%22,%22count%22:40,%22country%22:%22VE%22,%22keywords%22:%22{self.juego}%22,%22locale%22:%22es-ES%22,%22sortBy%22:%22relevancy,viewableDate%22,%22sortDir%22:%22DESC,DESC%22,%22start%22:0,%22tag%22:%229547%22,%22withPrice%22:true%7D&extensions=%7B%22persistedQuery%22:%7B%22version%22:1,%22sha256Hash%22:%227d58e12d9dd8cb14c84a3ff18d360bf9f0caa96bf218f2c5fda68ba88d68a437%22%7D%7D"
        self.start_urls = [url]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        data = json.loads(response.body)
        elements = data['data']['Catalog']['searchStore']['elements']

        # VALIDATE SEARCH
        if len(elements) > 0:
            element = filter(lambda x: (f'{self.juego} Standard Edition' in ' '.join(x['title'].replace('®', ' ').split())), elements)

            # VALIDATE FILTER
            if len(list(element)) == 0:
                element = elements[0]
            else:
                element = list(element)

            # GET DATA
            game = Juego()

            # NAME OPERATIONS
            modiNombre = ' '.join(re.findall(r'[a-zA-Z0-9]+', element['title']))
            editionName = re.search(r'(Standard Edition)', element['title'])
            game['nombre'] = str(element['title'])[0:editionName.start()] if editionName else element['title']
            modiNombre = str(modiNombre)[0:editionName.start()] if editionName else modiNombre
            modiNombre = str(''.join(map(lambda x: (x if len(x) == 1 else ' ' + x), modiNombre.split()))).strip()

            game['precio'] = element['price']['totalPrice']['fmtPrice']['originalPrice']
            game['descripcion'] = element['description']
            game['descuento'] = element['price']['totalPrice']['fmtPrice']['discountPrice']
            game['link'] = 'https://store.epicgames.com/es-ES/p/' + element['catalogNs']['mappings'][0]['pageSlug']
            game['img'] = element['keyImages'][2]['url']

            # CLEAN PRICES
            game['precio'] = float(game['precio'].replace('\xa0US$', '').replace(',', '.'))
            game['descuento'] = float(game['descuento'].replace('\xa0US$', '').replace(',', '.'))

            # CHECK DISCOUNT
            if game['descuento'] == game['precio']:
                game['descuento'] = None

            # CHECK GAME NAME NUMBERS
            if re.search(r'[0-9]+', self.juego):
                numberFound = re.finditer( r'[0-9]+', self.juego)
                nameConverted = [self.juego[0:m.start()] + roman.toRoman(int(self.juego[m.start():m.end()])) + self.juego[m.end():-1] for m in numberFound][0]
                
                if (game['precio'] != 0.0) and (re.search(rf'.*{self.juego.lower()}.*', modiNombre.lower()) or re.search(rf'.*{nameConverted.lower()}.*', modiNombre.lower())):
                    yield {'egs': dict(game)} 
                else:
                    yield {'egs': None}
            else:

                if (game['precio'] != 0.0) and (re.search(rf'.*{self.juego.lower()}.*', modiNombre.lower())):
                    yield {'egs': dict(game)} 
                else:
                    yield {'egs': None}
        else:
            yield {'egs': None}