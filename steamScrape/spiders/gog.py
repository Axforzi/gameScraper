import scrapy
from ..items import Juego
import json
import re
import roman

class GogSpider(scrapy.Spider):
    name = "gog"

    def __init__(self, juego, *args, **kwargs):
        super(GogSpider).__init__(*args, **kwargs)
        self.juego = ' '.join(re.findall(r'[a-zA-Z0-9]+', juego))
        self.start_urls = [f'https://catalog.gog.com/v1/catalog?limit=48&query=like%3A{self.juego}&order=asc%3Atitle&productType=in%3Agame%2Cpack%2C&page=1&countryCode=US&locale=en-US&currencyCode=USD']

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        game = Juego()
        data = json.loads(response.body)
        
        for i in range(len(data['products'])):

            # NAME OPERATIONS
            modiNombre = ' '.join(re.findall(r'[a-zA-Z0-9]+', data['products'][i]['title']))
            modiNombre = str(''.join(map(lambda x: (x if len(x) == 1 else ' ' + x), modiNombre.split()))).strip()
            game['nombre'] = data['products'][i]['title']

            game['precio'] = float(data['products'][i]['price']['base'].replace('$', ''))
            game['descuento'] = float(data['products'][i]['price']['final'].replace('$', ''))
            game['link'] = data['products'][i]['storeLink']
            game['img'] = data['products'][i]['coverVertical']
            if game['precio'] == game['descuento']:
                game['descuento'] = None

            # CHECK NAME NUMBER
            if re.search(r'[0-9]+', self.juego):
                numberFound = re.finditer( r'[0-9]+', self.juego)
                nameConverted = [self.juego[0:m.start()] + roman.toRoman(int(self.juego[m.start():m.end()])) + self.juego[m.end():-1] for m in numberFound][0]

                if (game['precio'] != 0) and (re.search(rf'.*{self.juego.lower()}.*', modiNombre.lower()) or re.search(rf'.*{nameConverted.lower()}.*', modiNombre.lower())):
                    return scrapy.Request(url=game['link'], callback=self.get_description, cb_kwargs={'game': game})
            
            else:
                if (game['precio'] != 0) and (re.search(rf'.*{self.juego.lower()}.*', modiNombre.lower())):
                    return scrapy.Request(url=game['link'], callback=self.get_description, cb_kwargs={'game': game})
            
        return {'gog': None}

    def get_description(self, response, game): 
        descriptionList = response.css('.description::text').getall()
        description = ''
        for p in descriptionList:
            description += p.strip()
        game['descripcion'] = description
        return {'gog': dict(game)}