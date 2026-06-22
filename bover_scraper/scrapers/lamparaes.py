"""Scraper for lampara.es (Spain)."""

from .playwright_base import PlaywrightScraper


class LamparaEsScraper(PlaywrightScraper):
    retailer = "Lampara.es"
    country = "ES"
    base_url = "https://www.lampara.es"

    BOVER_PAGES = [
        "https://www.lampara.es/c/todas-las-marcas/bover",
        "https://www.lampara.es/c/todas-las-marcas/bover?page=2",
        "https://www.lampara.es/c/todas-las-marcas/bover?page=3",
    ]
