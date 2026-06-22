"""Scraper for prediger.de (Germany) — uses Playwright."""

from .playwright_base import PlaywrightScraper


class PredigerScraper(PlaywrightScraper):
    retailer = "Prediger"
    country = "DE"
    base_url = "https://prediger.de"

    BOVER_PAGES = [
        "https://prediger.de/bover.html",
    ]
