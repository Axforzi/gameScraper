# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class Juego(scrapy.Item):
    nombre = scrapy.Field()
    descripcion = scrapy.Field()
    precio = scrapy.Field()
    descuento = scrapy.Field()
    img = scrapy.Field()
    link = scrapy.Field()

class Search(scrapy.Item):
    nombre = scrapy.Field()
    fuente = scrapy.Field()
    link = scrapy.Field()