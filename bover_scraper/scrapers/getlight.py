"""Scraper for getlight.de (Germany) — uses Playwright."""

from .playwright_base import PlaywrightScraper


class GetLightScraper(PlaywrightScraper):
    retailer = "GetLight"
    country = "DE"
    base_url = "https://www.getlight.de"

    BOVER_PAGES = [
        "https://www.getlight.de/bover/",
        "https://www.getlight.de/bover/?page=2",
        "https://www.getlight.de/bover/?page=3",
    ]
