"""Scraper for reuter.com (Germany) — uses Playwright."""

from .playwright_base import PlaywrightScraper


class ReuterScraper(PlaywrightScraper):
    retailer = "Reuter"
    country = "DE"
    base_url = "https://www.reuter.com"

    BOVER_PAGES = [
        "https://www.reuter.com/brands/bover.html",
        "https://www.reuter.com/brands/bover.html?p=2",
    ]
