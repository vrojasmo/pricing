"""
Generic Playwright-based scraper for sites that block plain HTTP requests.
Subclass this and set retailer, country, base_url and BOVER_PAGES.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .base import BaseScraper, ProductPrice, normalise_name, parse_price

logger = logging.getLogger(__name__)

# CSS selectors tried in order to find product cards
CARD_SELECTORS = [
    "li.product",
    ".product-item",
    "article.product",
    ".product-box",
    ".product-card",
    "[class*='product-list'] li",
    "[class*='ProductItem']",
    "[class*='product_item']",
    "div[data-product-id]",
]

NAME_SELECTORS = [
    "h2", "h3",
    ".product-name", ".product-title",
    "[class*='name']", "[class*='title']",
    "a.product_name",
]

PRICE_SELECTORS = [
    "[data-price-type='finalPrice'] .price",
    ".special-price .price",
    "span[itemprop='price']",
    ".price",
    "[class*='price']",
]


class PlaywrightScraper(BaseScraper):
    """Drives a real browser to scrape JS-heavy or bot-protected pages."""

    BOVER_PAGES: list[str] = []

    def scrape(self) -> list[ProductPrice]:
        results: list[ProductPrice] = []

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed")
            return results

        # Support custom chromium path via env var (useful in restricted envs)
        import os
        chromium_path = os.environ.get("CHROMIUM_PATH") or None

        with sync_playwright() as pw:
            launch_kwargs: dict = {
                "headless": True,
                "args": ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors"],
            }
            if chromium_path:
                launch_kwargs["executable_path"] = chromium_path

            browser = pw.chromium.launch(**launch_kwargs)
            context = browser.new_context(
                user_agent=self.HEADERS["User-Agent"],
                locale="de-DE" if self.country == "DE" else "es-ES",
                viewport={"width": 1440, "height": 900},
            )
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = context.new_page()

            for page_url in self.BOVER_PAGES:
                try:
                    page.goto(page_url, wait_until="domcontentloaded", timeout=40_000)
                    page.wait_for_timeout(2500)

                    # dismiss cookie banners
                    for btn_text in ["Akzeptieren", "Alle akzeptieren", "Accept", "Aceptar", "Accepter"]:
                        try:
                            page.click(f"button:has-text('{btn_text}')", timeout=2000)
                            break
                        except Exception:
                            pass

                    # scroll to trigger lazy loads
                    for _ in range(3):
                        page.evaluate("window.scrollBy(0, window.innerHeight)")
                        page.wait_for_timeout(700)

                    page_results = self._extract_products(page, page_url)
                    results.extend(page_results)

                    # check for "no more products" condition
                    if not page_results:
                        break

                except Exception as exc:
                    logger.warning("%s page error %s: %s", self.retailer, page_url, exc)

            browser.close()

        logger.info("%s: %d products scraped", self.retailer, len(results))
        return results

    def _extract_products(self, page, page_url: str) -> list[ProductPrice]:
        results: list[ProductPrice] = []

        # Try each card selector until we find something
        cards = []
        for sel in CARD_SELECTORS:
            cards = page.query_selector_all(sel)
            if cards:
                break

        if not cards:
            # Fallback: look for price elements and walk up to find names
            results.extend(self._fallback_extract(page, page_url))
            return results

        for card in cards:
            name_el = None
            for sel in NAME_SELECTORS:
                name_el = card.query_selector(sel)
                if name_el:
                    break

            price_el = None
            for sel in PRICE_SELECTORS:
                price_el = card.query_selector(sel)
                if price_el:
                    break

            if not name_el or not price_el:
                continue

            raw_name = name_el.inner_text().strip()
            raw_price = price_el.inner_text().strip()
            price = parse_price(raw_price)
            if price is None or price <= 0:
                continue

            link_el = card.query_selector("a[href]")
            url = link_el.get_attribute("href") if link_el else page_url
            if url and url.startswith("/"):
                url = self.base_url + url

            results.append(ProductPrice(
                retailer=self.retailer,
                country=self.country,
                product_name=raw_name,
                product_name_norm=normalise_name(raw_name),
                url=url or page_url,
                price=price,
                scraped_at=datetime.now(timezone.utc).isoformat(),
            ))

        return results

    def _fallback_extract(self, page, page_url: str) -> list[ProductPrice]:
        """
        Last resort: find JSON-LD structured data or meta tags with product info.
        """
        results: list[ProductPrice] = []
        import json

        scripts = page.query_selector_all("script[type='application/ld+json']")
        for script in scripts:
            try:
                data = json.loads(script.inner_text())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") not in ("Product", "ItemList"):
                        continue
                    if item.get("@type") == "ItemList":
                        for el in item.get("itemListElement", []):
                            item2 = el.get("item", el)
                            p = self._from_jsonld(item2, page_url)
                            if p:
                                results.append(p)
                    else:
                        p = self._from_jsonld(item, page_url)
                        if p:
                            results.append(p)
            except Exception:
                pass

        return results

    def _from_jsonld(self, item: dict, fallback_url: str) -> Optional[ProductPrice]:
        name = item.get("name", "")
        if not name:
            return None
        offers = item.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price_str = str(offers.get("price", ""))
        price = parse_price(price_str)
        if price is None:
            return None
        url = item.get("url", fallback_url)
        return ProductPrice(
            retailer=self.retailer,
            country=self.country,
            product_name=name,
            product_name_norm=normalise_name(name),
            url=url,
            price=price,
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )
