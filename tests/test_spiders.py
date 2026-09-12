"""Spider parse tests against cached fixtures (REQ-TST-4).

No network is ever touched: every response is built from a fixture under
``tests/fixtures/``. Malformed entries ("Free!", "Free", "Gratis") must be
logged and skipped — never crash the parse.
"""

import scrapy
from conftest import read_fixture
from scrapy.http import HtmlResponse, TextResponse

from steamScrape.spiders.epicgames import EpicgamesSpider
from steamScrape.spiders.gog import GogSpider
from steamScrape.spiders.offers_egs import OffersEgsSpider
from steamScrape.spiders.offers_gog import OffersGogSpider
from steamScrape.spiders.offers_steam import OffersSteamSpider
from steamScrape.spiders.steam import SteamSpider

GAME_URL = "https://store.steampowered.com/app/70/Half-Life/"
GOG_URL = "https://catalog.gog.com/v1/catalog?limit=48"
EGS_URL = "https://store.epicgames.com/graphql?operationName=searchStoreQuery"


def make_html(url: str, fixture: str, request=None) -> HtmlResponse:
    return HtmlResponse(
        url=url,
        body=read_fixture(fixture),
        encoding="utf-8",
        request=request or scrapy.Request(url=url),
    )


def make_json(url: str, fixture: str) -> TextResponse:
    return TextResponse(
        url=url,
        body=read_fixture(fixture),
        encoding="utf-8",
        request=scrapy.Request(url=url),
    )


class TestSteamSpider:
    def test_search_found_follows_to_game_page(self) -> None:
        spider = SteamSpider(juego="portal")
        response = make_html(
            "https://store.steampowered.com/search/?term=portal", "html/steam_search.html"
        )
        results = list(spider.search_game(response))
        assert len(results) == 1
        request = results[0]
        assert isinstance(request, scrapy.Request)
        assert request.url == "https://store.steampowered.com/app/123456/Portal/"
        assert request.callback == spider.parse

    def test_search_without_results_yields_none(self) -> None:
        spider = SteamSpider(juego="doesnotexist")
        response = make_html(
            "https://store.steampowered.com/search/?term=doesnotexist",
            "html/steam_search_empty.html",
        )
        assert list(spider.search_game(response)) == [{"steam": None}]

    def test_parse_without_discount(self) -> None:
        spider = SteamSpider(juego="test game")
        response = make_html(GAME_URL, "html/steam_game.html")
        (result,) = list(spider.parse(response))
        assert result == {
            "steam": {
                "nombre": "Test Game",  # trademark symbol stripped
                "descripcion": "A test game description.",
                "link": GAME_URL,
                "img": "https://cdn.steam/apps/123456/header.jpg",
                "precio": 19.99,
                "descuento": None,
            }
        }

    def test_parse_with_discount(self) -> None:
        spider = SteamSpider(juego="half-life 2")
        response = make_html(GAME_URL, "html/steam_game_discount.html")
        (result,) = list(spider.parse(response))
        assert result["steam"]["nombre"] == "Half-Life 2"
        assert result["steam"]["precio"] == 29.99
        assert result["steam"]["descuento"] == 14.99

    def test_parse_malformed_price_is_logged_not_fatal(self, caplog) -> None:
        spider = SteamSpider(juego="free game")
        response = make_html(GAME_URL, "html/steam_game_malformed.html")
        assert list(spider.parse(response)) == [{"steam": None}]
        assert "malformed price" in caplog.text


class TestGogSpider:
    def test_parse_matches_roman_numeral_product(self) -> None:
        spider = GogSpider(juego="final fantasy 4")
        response = make_json(GOG_URL, "json/gog_catalog.json")
        request = spider.parse(response)  # returns, not yields

        assert isinstance(request, scrapy.Request)
        assert request.callback == spider.get_description
        game = request.cb_kwargs["game"]
        assert game["nombre"] == "Final Fantasy IV"
        assert game["link"] == "https://www.gog.com/game/final_fantasy_iv"
        assert game["precio"] == 49.99
        assert game["descuento"] == 24.99

    def test_parse_skips_malformed_product_and_returns_none(self, caplog) -> None:
        spider = GogSpider(juego="zzzz")
        response = make_json(GOG_URL, "json/gog_catalog.json")
        assert spider.parse(response) == {"gog": None}
        assert "malformed product" in caplog.text

    def test_parse_skips_null_price_candidate_without_crash(self) -> None:
        spider = GogSpider(juego="null price game")
        response = make_json(GOG_URL, "json/gog_catalog.json")
        assert spider.parse(response) == {"gog": None}

    def test_parse_skips_null_price_product_silently(self, caplog) -> None:
        spider = GogSpider(juego="null price game")
        response = make_json(GOG_URL, "json/gog_null_price.json")
        assert spider.parse(response) == {"gog": None}
        assert "malformed product" not in caplog.text

    def test_get_description_joins_snippets(self) -> None:
        spider = GogSpider(juego="witcher")
        response = make_html(
            "https://www.gog.com/game/the_witcher_3_wild_hunt", "html/gog_game.html"
        )
        game = {"nombre": "The Witcher 3: Wild Hunt", "precio": 19.99, "descuento": None}
        result = spider.get_description(response, game)
        assert result == {
            "gog": {
                "nombre": "The Witcher 3: Wild Hunt",
                "precio": 19.99,
                "descuento": None,
                "descripcion": "An epic RPG." + "And the expansions.",
            }
        }


class TestEpicgamesSpider:
    def test_parse_matches_roman_numeral_element(self) -> None:
        spider = EpicgamesSpider(juego="final fantasy 4")
        response = make_json(EGS_URL, "json/egs_graphql.json")
        (result,) = list(spider.parse(response))
        game = result["egs"]
        assert game["nombre"] == "Final Fantasy IV"
        assert game["precio"] == 59.99
        assert game["descuento"] == 29.99
        assert game["link"] == "https://store.epicgames.com/es-ES/p/final-fantasy-iv"
        assert game["img"] == "https://cdn.epic/ff4.jpg"
        assert game["descripcion"] == "A classic RPG."

    def test_parse_no_match_yields_none(self) -> None:
        spider = EpicgamesSpider(juego="zelda")
        response = make_json(EGS_URL, "json/egs_graphql.json")
        assert list(spider.parse(response)) == [{"egs": None}]

    def test_parse_malformed_top_hit_is_logged_not_fatal(self, caplog) -> None:
        spider = EpicgamesSpider(juego="free game")
        response = make_json(EGS_URL, "json/egs_game_malformed.json")
        assert list(spider.parse(response)) == [{"egs": None}]
        assert "malformed price" in caplog.text


class TestOffersSteamSpider:
    def test_start_requests_sends_age_gate_bypass(self) -> None:
        spider = OffersSteamSpider()
        (request,) = list(spider.start_requests())

        assert request.callback == spider.parse
        assert request.cookies == spider.cookiesConfig
        accept_language = request.headers.get("Accept-Language")
        assert accept_language is not None
        assert "es-ES" in accept_language.decode()

    def test_parse_skips_malformed_offer_and_follows_valid_ones(self, caplog) -> None:
        spider = OffersSteamSpider()
        response = make_html(
            "https://store.steampowered.com/search/?specials=1", "html/steam_offers.html"
        )
        requests = list(spider.parse(response))

        assert len(requests) == 2  # middle offer with "Free!" prices is skipped
        first = requests[0].meta["game"]
        assert first["nombre"] == "Offer One"
        assert first["precio"] == 10.0
        assert first["descuento"] == 5.0
        assert first["link"] == "https://store.steampowered.com/app/111/Offer_One/"
        assert first["img"] == "https://cdn.steam/apps/111/capsule.jpg"
        assert requests[1].meta["game"]["nombre"] == "Offer Two"
        assert "malformed price" in caplog.text

    def test_parse_offer_uses_full_cover_when_available(self) -> None:
        spider = OffersSteamSpider()
        game_payload = {
            "nombre": "Offer One",
            "precio": 10.0,
            "descuento": 5.0,
            "link": "https://store.steampowered.com/app/111/Offer_One/",
            "img": "https://cdn.steam/apps/111/capsule.jpg",
        }
        request = scrapy.Request(url=GAME_URL, meta={"game": dict(game_payload)})
        response = make_html(GAME_URL, "html/steam_game.html", request=request)
        (result,) = list(spider.parse_offer(response))
        assert result["steam"][0]["img"] == "https://cdn.steam/apps/123456/header.jpg"

    def test_parse_offer_keeps_thumbnail_without_cover(self) -> None:
        spider = OffersSteamSpider()
        game_payload = {"nombre": "Offer One", "img": "https://cdn.steam/thumb.jpg"}
        request = scrapy.Request(url=GAME_URL, meta={"game": game_payload})
        response = make_html(GAME_URL, "html/steam_search_empty.html", request=request)
        (result,) = list(spider.parse_offer(response))
        assert result["steam"][0]["img"] == "https://cdn.steam/thumb.jpg"


class TestOffersGogSpider:
    def test_parse_skips_malformed_product(self, caplog) -> None:
        spider = OffersGogSpider()
        response = make_json(GOG_URL, "json/gog_catalog.json")
        (result,) = list(spider.parse(response))

        games = result["gog"]
        assert len(games) == 8  # top-9 slice, "Free"/"Free" product skipped
        assert games[0]["nombre"] == "The Witcher 3: Wild Hunt"
        assert games[0]["precio"] == 39.99
        assert games[0]["descuento"] == 19.99
        assert "malformed product" in caplog.text


class TestOffersEgsSpider:
    def test_start_url_has_no_stale_effective_date_filter(self) -> None:
        spider = OffersEgsSpider()
        (url,) = spider.start_urls
        assert "effectiveDate" not in url

    def test_parse_skips_malformed_element(self, caplog) -> None:
        spider = OffersEgsSpider()
        response = make_json(EGS_URL, "json/egs_graphql.json")
        (result,) = list(spider.parse(response))

        games = result["egs"]
        assert len(games) == 8  # top-9 slice, "Gratis" element skipped
        assert games[0]["nombre"] == "Final Fantasy IV"
        assert games[0]["precio"] == 59.99
        assert games[0]["descuento"] == 29.99
        assert games[0]["link"] == "https://store.epicgames.com/es-ES/p/final-fantasy-iv"
        assert "malformed product" in caplog.text