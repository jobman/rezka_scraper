from operator import index
from requests import request
import scrapy
from bs4 import BeautifulSoup
import json
import time
import re
from scrapy import item
from ..items import RezkaScraperItem
import os.path
from os import path
import requests


class FilmSpider(scrapy.Spider):
    rezka_host = "http://kinopub.me/"
    name = "films"
    page = 901
    last_page = 947
    start_urls = [f"{rezka_host}films/page/901/?filter=popular"]

    def parse(self, response, **kwargs):
        """
        films_on_page_urls = (
            response.css(".b-content__inline_item-link a")
            .css("a::attr(href)")
            .extract()
        )
        """
        # read films_on_page_urls from file "missing_films.txt"
        with open("missing_films.txt", "r") as f:
            films_on_page_urls = f.read().split("\n")

        for film_url in films_on_page_urls:
            # news_id = film_url.split("/")[-1].split("-")[0]
            yield response.follow(film_url, callback=self.parse_film_page)
        """
        if FilmSpider.page <= FilmSpider.last_page:
            FilmSpider.page += 1

            next_page = (
                f"{self.rezka_host}films/page/"
                + str(FilmSpider.page)
                + "/?filter=popular"
            )
            yield response.follow(next_page, callback=self.parse)
        """

    def parse_comments_html(self, html):
        final_result = []

        soup = BeautifulSoup(html, "html.parser")
        for comment_tree in soup.find_all("li", class_="comments-tree-item"):
            if comment_tree.attrs["data-indent"] != "0":
                continue
            message_html = str(comment_tree.find("div", class_="message"))
            if message_html.find("<!--dle_spoiler-->") != -1:
                message_html = message_html.replace(">спойлер<", "> <")
                message_html = message_html.replace(
                    "<!--spoiler_text-->", "###OPEN_SPOILER###"
                )
                message_html = message_html.replace(
                    "<!--spoiler_text_end-->", "###CLOSE_SPOILER###"
                )
                message_soup = BeautifulSoup(message_html, "html.parser")
            else:
                message_soup = BeautifulSoup(message_html, "html.parser")
            res = message_soup.find("div", class_="text").find("div").text
            comment_parts = []
            for part in res.split("\n"):
                clear_part = part.strip()
                if clear_part.find("###OPEN_SPOILER###") != -1:
                    clear_part = clear_part.replace(
                        "###OPEN_SPOILER###", "<tg-spoiler>"
                    )
                if clear_part.find("###CLOSE_SPOILER###") != -1:
                    clear_part = clear_part.replace(
                        "###CLOSE_SPOILER###", "</tg-spoiler>"
                    )
                comment_parts.append(clear_part)
            comment_parts = list(filter(lambda x: x != "", comment_parts))
            res = " ".join(comment_parts)
            message_text = res.strip()
            message_likes = (
                message_soup.find(class_="b-comment__likes_count")
                .text.replace(")", "")
                .replace("(", "")
            )
            final_result.append((message_text, int(message_likes)))
        return final_result

    def parse_comments_api(self, response, **kwargs):
        news_id = kwargs["news_id"]

        if not path.exists(f"{news_id}.txt"):
            comments_string = json.dumps([])
            with open(f"comments/{news_id}.txt", "w") as f:
                f.write(comments_string)

        data = json.loads(response.body)
        comments_html_unicode = data["comments"]
        comments_html_text = comments_html_unicode.encode("utf-8").decode("utf-8")
        comments = self.parse_comments_html(comments_html_text)
        if comments:
            with open(f"comments/{news_id}.txt", "r") as f:
                comments_string = f.read()
            old_comments = json.loads(comments_string)
            old_comments.extend(comments)
            old_comments.sort(key=lambda x: x[1], reverse=True)
            comments_json_to_write = json.dumps(old_comments)
            with open(f"comments/{news_id}.txt", "w") as f:
                f.write(comments_json_to_write)
        navigation_html = data["navigation"]

        if navigation_html.find("b-navigation__next") == -1:
            next_page = None
        else:
            all_javascript_calls = re.findall(
                "[0-9]*, [0-9]*, false, 0", navigation_html
            )
            next_page = int(all_javascript_calls[-1].split(",")[1][1:])

        link = kwargs["link"]
        new_link = link.replace(
            re.findall("cstart=[0-9]+&", link)[0], "cstart=" + str(next_page) + "&"
        )
        if next_page:
            # time.sleep(1)
            yield scrapy.Request(
                new_link,
                callback=self.parse_comments_api,
                cb_kwargs={
                    "page": next_page,
                    "news_id": kwargs["news_id"],
                    "headers": kwargs["headers"],
                    "link": kwargs["link"],
                },
            )

    def parse_comments(self, response, **kwargs):

        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": response.url,
            "sec-ch-ua": '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }
        page = kwargs["page"]
        news_id = kwargs["news_id"]

        link = f"{self.rezka_host}ajax/get_comments/?t={time.time()-100}&news_id={news_id}&cstart={page}&type=0&comment_id=0&skin=hdrezka"

        yield scrapy.Request(
            link,
            headers=headers,
            callback=self.parse_comments_api,
            cb_kwargs={
                "page": page,
                "news_id": news_id,
                "headers": headers,
                "link": link,
            },
        )

    def parse_film_page(self, response, **kwargs):
        item = RezkaScraperItem()
        genere_list = response.css("td > a span").css("::text").getall()
        for e in genere_list:
            for symbol in e:
                if not symbol.isalpha():
                    e = e.replace(symbol, "_")
        item["genre"] = " ".join(["#" + genre for genre in genere_list])
        producer_list = [
            producer
            for producer in response.css(".l+ td .persons-list-holder")
            .css("::text")
            .getall()
            if producer.replace(" ", "")
        ]
        for e, index in zip(producer_list, range(len(producer_list))):
            for symbol in e:
                if not symbol.isalpha():
                    producer_list[index] = producer_list[index].replace(symbol, "_")
        producer_list_with_hashtag = ["#" + producer for producer in producer_list]
        " ".join(producer_list_with_hashtag)
        item["producer"] = " ".join(producer_list_with_hashtag)
        info_list = response.css(".b-post__infotable_right_inner").css("tr").getall()
        info_soup = BeautifulSoup(" ".join(info_list), "html.parser")
        for row in info_soup.find_all("tr"):
            if row.find("td").text.find("Дата выхода") != -1:
                date_string = row.find_all("td")[1].text
                break
        else:
            date_string = None

        if date_string:
            year = re.findall("[0-9]{4}", date_string)[0]
            date_string = date_string.replace(year + " ", "#" + year)
            date_decade = int(year) - int(year) % 10
            year_dict = {
                1900: "#1900s",
                1910: "#1910s",
                1920: "#1920s",
                1930: "#1930s",
                1940: "#1940s",
                1950: "#1950s",
                1960: "#1960s",
                1970: "#1970s",
                1980: "#1980s",
                1990: "#1990s",
                2000: "#2000s",
                2010: "#2010s",
                2020: "#2020s",
            }
            date_sufix = year_dict[date_decade] if date_decade in year_dict else ""
            item["date"] = date_string + " " + date_sufix
        else:
            item["date"] = ""
        cast_list = [
            e
            for e in response.css("td:nth-child(1) .item").css("::text").getall()
            if not (e == "," or e == "и другие")
        ]
        # replace not alphabetical characters with '_' in cats_list
        for e, index in zip(cast_list, range(len(cast_list))):
            for symbol in e:
                if not symbol.isalpha():
                    cast_list[index] = cast_list[index].replace(symbol, "_")
        cast_list_with_hashtag = ["#" + e for e in cast_list]
        item["cast"] = " ".join(cast_list_with_hashtag)
        item["image_url"] = response.css(".b-sidecover img").css("::attr(src)").get()
        item["imdb"] = response.css(".imdb .bold").css("::text").get()
        item["film_name"] = response.css("h1::text").get().replace(",", "")
        item["film_url"] = response.url
        rating = response.css(".num::text").get()
        item["film_rating"] = rating if rating else "0"
        rating_count = response.css(".votes span").css("::text").get()
        item["film_rating_count"] = rating_count if rating_count else "0"
        news_id = response.url.split("/")[-1].split("-")[0]
        cb_kwargs = {
            "item": item,
            "page": 1,
            "news_id": news_id,
        }
        try:
            image_extension = item["image_url"].split(".")[-1]
            img_data = requests.get(item["image_url"]).content
            with open(f"posters/{news_id}.{image_extension}", "wb") as handler:
                handler.write(img_data)
                print(f"Poster saved to posters/{news_id}.{image_extension}")
        except Exception as e:
            print("Poster cant be saved, during exception", e)

        # yield self.parse_comments(response, **cb_kwargs)

        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": response.url,
            "sec-ch-ua": '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }
        page = cb_kwargs["page"]
        news_id = cb_kwargs["news_id"]
        item["film_id"] = news_id

        link = f"{self.rezka_host}ajax/get_comments/?t={time.time()-100}&news_id={news_id}&cstart={page}&type=0&comment_id=0&skin=hdrezka"

        yield scrapy.Request(
            link,
            headers=headers,
            callback=self.parse_comments_api,
            cb_kwargs={
                "page": page,
                "news_id": news_id,
                "headers": headers,
                "link": link,
            },
        )

        yield item
