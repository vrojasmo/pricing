"""
Matches scraped product names against the official price list using
a combination of exact normalised lookup and fuzzy token matching.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional

from .official_prices import OFFICIAL_PRICES, MAX_DISCOUNT_PCT
from .scrapers.base import ProductPrice


# Pre-compute token sets for all official keys
_OFFICIAL_TOKENS: dict[str, frozenset[str]] = {
    k: frozenset(re.split(r"[\s/]+", k)) for k in OFFICIAL_PRICES
}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _token_overlap(name_norm: str, official_key: str) -> float:
    """Jaccard-style overlap between token sets."""
    a_tokens = frozenset(re.split(r"[\s/]+", name_norm))
    b_tokens = _OFFICIAL_TOKENS[official_key]
    if not a_tokens or not b_tokens:
        return 0.0
    intersection = a_tokens & b_tokens
    union = a_tokens | b_tokens
    return len(intersection) / len(union)


def find_official_price(product: ProductPrice) -> Optional[tuple[str, float]]:
    """
    Return (matched_key, official_price) or None if no confident match found.
    Strategy:
      1. Exact match on normalised name.
      2. Best token-overlap + sequence similarity combined score.
    """
    norm = product.product_name_norm

    # 1. Exact lookup
    if norm in OFFICIAL_PRICES:
        return norm, OFFICIAL_PRICES[norm]

    # 2. Fuzzy: require that the scraped name contains "bover" or all key
    #    model tokens are present
    best_key: Optional[str] = None
    best_score: float = 0.0

    for key in OFFICIAL_PRICES:
        token_score = _token_overlap(norm, key)
        seq_score = _similarity(norm, key)
        combined = 0.6 * token_score + 0.4 * seq_score

        if combined > best_score:
            best_score = combined
            best_key = key

    if best_key and best_score >= 0.55:
        return best_key, OFFICIAL_PRICES[best_key]

    return None


def annotate_compliance(products: list[ProductPrice]) -> list[ProductPrice]:
    """Annotate each product with official_price, discount_pct, and compliant flag."""
    for p in products:
        match = find_official_price(p)
        if match:
            matched_key, official = match
            p.official_price = official
            p.discount_pct = round((1 - p.price / official) * 100, 2)
            p.compliant = p.discount_pct <= MAX_DISCOUNT_PCT
        else:
            p.official_price = None
            p.discount_pct = None
            p.compliant = None  # unknown — not in official catalogue
    return products
