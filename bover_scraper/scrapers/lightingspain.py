"""Scraper for lightingspain.com (Spain) — tries HTTP first, falls back to Playwright."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ProductPrice, normalise_name, parse_price
from .playwright_base import PlaywrightScraper

logger = logging.getLogger(__name__)

BOVER_PAGES = [
    "https://lightingspain.com/marcas/25-bover",
    "https://lightingspain.com/marcas/25-bover?p=2",
    "https://lightingspain.com/marcas/25-bover?p=3",
]


class LightingSpainScraper(PlaywrightScraper):
    retailer = "LightingSpain"
    country = "ES"
    base_url = "https://lightingspain.com"
    BOVER_PAGES = BOVER_PAGES
