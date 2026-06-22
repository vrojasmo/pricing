"""
Unit tests for the Bover price compliance scraper.
Run with: python -m pytest tests/ -v
"""

import pytest
from bover_scraper.scrapers.base import ProductPrice, normalise_name, parse_price
from bover_scraper.matcher import annotate_compliance, find_official_price
from bover_scraper.official_prices import OFFICIAL_PRICES, MAX_DISCOUNT_PCT


# ── parse_price ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    ("1.299,00 €",  1299.00),
    ("€449",        449.00),
    ("499,00",      499.00),
    ("1,299.00",    1299.00),
    ("395 €",       395.00),
    ("$1,200.00",   1200.00),
    ("649.00 €",    649.00),
    ("749",         749.00),
])
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


def test_parse_price_invalid():
    assert parse_price("out of stock") is None
    assert parse_price("") is None


# ── normalise_name ────────────────────────────────────────────────────────────

def test_normalise_name():
    assert normalise_name("Bover Kata P/01") == "bover kata p/01"
    assert normalise_name("  Bover  Nans  P/02  ") == "bover nans p/02"
    assert normalise_name("BOVER DOME P/03") == "bover dome p/03"


# ── find_official_price ───────────────────────────────────────────────────────

def test_exact_match():
    p = ProductPrice("R", "ES", "Bover Kata P/01", "bover kata p/01", "http://x", 499.0)
    result = find_official_price(p)
    assert result is not None
    key, price = result
    assert price == OFFICIAL_PRICES["bover kata p/01"]


def test_fuzzy_match():
    p = ProductPrice("R", "ES", "Bover Kata Pendant P/01 White", normalise_name("Bover Kata Pendant P/01 White"), "http://x", 450.0)
    result = find_official_price(p)
    assert result is not None
    _, price = result
    assert price == OFFICIAL_PRICES["bover kata p/01"]


def test_no_match_unknown_product():
    p = ProductPrice("R", "ES", "Flos Arco Floor", "flos arco floor", "http://x", 3000.0)
    result = find_official_price(p)
    assert result is None


# ── annotate_compliance ───────────────────────────────────────────────────────

def _make_product(name: str, price: float, country="ES") -> ProductPrice:
    return ProductPrice("TestShop", country, name, normalise_name(name), "http://x", price)


def test_compliant_at_exact_rrp():
    products = annotate_compliance([_make_product("Bover Kata P/01", 499.00)])
    p = products[0]
    assert p.compliant is True
    assert p.discount_pct == 0.0


def test_compliant_at_15pct_discount():
    rrp = OFFICIAL_PRICES["bover kata p/01"]  # 499.00
    price = round(rrp * 0.85, 2)             # exactly 15% off
    products = annotate_compliance([_make_product("Bover Kata P/01", price)])
    assert products[0].compliant is True
    assert abs(products[0].discount_pct - 15.0) < 0.05


def test_non_compliant_over_15pct():
    rrp = OFFICIAL_PRICES["bover kata p/01"]
    price = round(rrp * 0.84, 2)  # 16% off
    products = annotate_compliance([_make_product("Bover Kata P/01", price)])
    assert products[0].compliant is False
    assert products[0].discount_pct > 15.0


def test_unknown_product_is_none():
    products = annotate_compliance([_make_product("Some Other Brand", 100.0)])
    assert products[0].compliant is None
    assert products[0].official_price is None


def test_price_higher_than_rrp_compliant():
    """If retailer charges MORE than RRP, discount is negative — still compliant."""
    products = annotate_compliance([_make_product("Bover Kata P/01", 550.00)])
    assert products[0].compliant is True
    assert products[0].discount_pct < 0


def test_multiple_retailers_mixed_compliance():
    products = [
        _make_product("Bover Nans P/01",  395.00),           # 0% -> YES
        _make_product("Bover Nans P/01",  round(395*0.84, 2)), # ~16% -> NO
        _make_product("Bover Nans P/02",  445.00),           # 0%  -> YES
        _make_product("Unknown lamp xyz", 200.00),           # unknown
    ]
    products = annotate_compliance(products)
    statuses = [p.compliant for p in products]
    assert statuses == [True, False, True, None]


# ── official price list sanity ────────────────────────────────────────────────

def test_official_prices_non_empty():
    assert len(OFFICIAL_PRICES) > 50


def test_max_discount_is_15():
    assert MAX_DISCOUNT_PCT == 15.0


def test_all_prices_positive():
    for key, price in OFFICIAL_PRICES.items():
        assert price > 0, f"Non-positive price for {key}"
