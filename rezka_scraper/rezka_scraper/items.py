# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class RezkaScraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    film_name = scrapy.Field()
    film_url = scrapy.Field()
    film_rating = scrapy.Field()
    film_rating_count = scrapy.Field()
    genre = scrapy.Field()
    producer = scrapy.Field()
    cast = scrapy.Field()
    date = scrapy.Field()
    image_url = scrapy.Field()
    imdb = scrapy.Field()
    film_id = scrapy.Field()
