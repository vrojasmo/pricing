"""Scraper for mylightshop.com (Spain)."""

from .playwright_base import PlaywrightScraper


class MyLightShopScraper(PlaywrightScraper):
    retailer = "MyLightShop"
    country = "ES"
    base_url = "https://www.mylightshop.com"

    BOVER_PAGES = [
        "https://www.mylightshop.com/bover.html",
        "https://www.mylightshop.com/bover.html?p=2",
        "https://www.mylightshop.com/bover.html?p=3",
    ]
