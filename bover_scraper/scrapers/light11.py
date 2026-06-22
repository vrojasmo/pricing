"""Scraper for light11.eu (Germany) — uses Playwright (site blocks plain HTTP)."""

from .playwright_base import PlaywrightScraper


class Light11Scraper(PlaywrightScraper):
    retailer = "Light11"
    country = "DE"
    base_url = "https://www.light11.eu"

    BOVER_PAGES = [
        "https://www.light11.eu/bover/",
        "https://www.light11.eu/bover/?page=2",
        "https://www.light11.eu/bover/?page=3",
    ]
