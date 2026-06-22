"""Base scraper interface and shared helpers."""

from __future__ import annotations

import re
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ProductPrice:
    retailer: str
    country: str          # "ES" or "DE"
    product_name: str     # as shown on the website
    product_name_norm: str  # normalised for matching
    url: str
    price: float
    currency: str = "EUR"
    in_stock: bool = True
    scraped_at: str = ""
    official_price: Optional[float] = None
    discount_pct: Optional[float] = None
    compliant: Optional[bool] = None   # True = respects the 15% max discount rule


def normalise_name(name: str) -> str:
    """Lower-case, collapse whitespace, remove special chars for fuzzy matching."""
    name = name.lower()
    name = re.sub(r"[^\w\s/]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def parse_price(raw: str) -> Optional[float]:
    """Extract float price from strings like '1.299,00 €', '€449', '$1,299.00'."""
    # remove currency symbols and spaces
    raw = re.sub(r"[€$£\s]", "", raw)
    # European format: 1.299,00 -> 1299.00
    if re.match(r"^\d{1,3}(\.\d{3})*(,\d{1,2})?$", raw):
        raw = raw.replace(".", "").replace(",", ".")
    else:
        # remove any remaining commas (US thousands separator)
        raw = raw.replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


class BaseScraper:
    """All site scrapers extend this class."""

    retailer: str = ""
    country: str = ""
    base_url: str = ""

    HEADERS: dict = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def scrape(self) -> list[ProductPrice]:
        raise NotImplementedError

    def _sleep(self, seconds: float = 1.5) -> None:
        time.sleep(seconds)
