import scrapy
from bs4 import BeautifulSoup
import requests
from ..items import Juego

class OffersSteamSpider(scrapy.Spider):
    name = "offers_steam"
    start_urls = ["https://store.steampowered.com/search/?category1=998&os=win&specials=1&ndl=1"]

    def parse(self, response):
        game = Juego()
        content = response.xpath("//div[@class='search_results']//a[@data-gpnav='item']")[0:10]

        games = []
        for element in content:
            game['nombre'] = element.css('.title::text').get().strip()
            game['precio'] = float(element.css('.discount_original_price::text').get().strip().replace('$', ''))
            game['descuento'] = float(element.css('.discount_final_price::text').get().strip().replace('$', ''))
            game['link'] = element.css("::attr('href')").get()

            # GET IMG LINK
            img = element.css("img::attr('src')").get().split('/')
            img = '/'.join(img)
            game['img'] = img

            session = requests.Session()
            r = session.get(game['link'])
            soup = BeautifulSoup(r.text, 'html.parser')
            game['img'] = soup.find('img', {'class': 'game_header_image_full'}).get('src')

            games.append(dict(game))

        yield {'steam': games}