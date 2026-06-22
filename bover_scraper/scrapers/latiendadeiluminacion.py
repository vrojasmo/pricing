"""Scraper for latiendadeiluminacion.com (Spain)."""

from .playwright_base import PlaywrightScraper


class LaTiendaDeIluminacionScraper(PlaywrightScraper):
    retailer = "LaTiendaDeIluminacion"
    country = "ES"
    base_url = "https://www.latiendadeiluminacion.com"

    BOVER_PAGES = [
        "https://www.latiendadeiluminacion.com/en/brand/8-bover",
        "https://www.latiendadeiluminacion.com/en/brand/8-bover?p=2",
        "https://www.latiendadeiluminacion.com/en/brand/8-bover?p=3",
    ]
