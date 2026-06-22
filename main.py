#!/usr/bin/env python3
"""
Bover Price Compliance Scraper
===============================
Scrapes Bover product prices from authorized retailers in Spain (ES)
and Germany (DE), compares them against the official RRP, and flags
any retailer giving more than 15% discount.

Usage
-----
  # Full run (all retailers, all countries)
  python main.py

  # Only Spain
  python main.py --country ES

  # Only Germany
  python main.py --country DE

  # Specific retailers
  python main.py --retailers light11 getlight

  # Skip reports, just print to console
  python main.py --no-excel --no-csv

  # Custom output directory
  python main.py --output reports/

  # Add official price CSV to seed the price list
  python main.py --prices my_bover_prices.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bover_scraper.scrapers import ALL_SCRAPERS
from bover_scraper.scrapers.base import ProductPrice
from bover_scraper.matcher import annotate_compliance
from bover_scraper.reporter import (
    save_excel,
    save_csv,
    save_json,
    print_console_summary,
)
import bover_scraper.official_prices as official_prices_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def load_custom_prices(path: Path) -> None:
    """
    Load official prices from a CSV with columns: product_name, price
    and merge them into OFFICIAL_PRICES at runtime.
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("product_name", "").strip().lower()
            try:
                price = float(row["price"])
            except (KeyError, ValueError):
                continue
            if name:
                official_prices_module.OFFICIAL_PRICES[name] = price
    logger.info("Loaded custom prices from %s (%d total entries)", path, len(official_prices_module.OFFICIAL_PRICES))


def run_scraper(scraper_cls) -> list[ProductPrice]:
    try:
        scraper = scraper_cls()
        return scraper.scrape()
    except Exception as exc:
        logger.error("Scraper %s failed: %s", scraper_cls.__name__, exc, exc_info=True)
        return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Bover price compliance scraper")
    parser.add_argument(
        "--country", choices=["ES", "DE"],
        help="Limit scraping to one country (ES=Spain, DE=Germany)"
    )
    parser.add_argument(
        "--retailers", nargs="+", metavar="NAME",
        help="Comma-separated retailer names to include (e.g. light11 getlight)"
    )
    parser.add_argument(
        "--output", default="reports", metavar="DIR",
        help="Directory for output files (default: reports/)"
    )
    parser.add_argument("--no-excel", action="store_true", help="Skip Excel output")
    parser.add_argument("--no-csv",   action="store_true", help="Skip CSV output")
    parser.add_argument("--no-json",  action="store_true", help="Skip JSON output")
    parser.add_argument(
        "--prices", metavar="CSV",
        help="Path to CSV file with custom official prices (columns: product_name, price)"
    )
    parser.add_argument(
        "--workers", type=int, default=4,
        help="Number of parallel scraper threads (default: 4)"
    )
    args = parser.parse_args()

    # Load custom price list if provided
    if args.prices:
        load_custom_prices(Path(args.prices))

    # Filter scrapers
    scrapers = ALL_SCRAPERS
    if args.country:
        scrapers = [s for s in scrapers if s.country == args.country]
    if args.retailers:
        names_lower = {n.lower() for n in args.retailers}
        scrapers = [s for s in scrapers if s.retailer.lower() in names_lower]

    if not scrapers:
        logger.error("No scrapers matched the given filters.")
        return 1

    logger.info(
        "Starting scrape: %d retailer(s) in %s",
        len(scrapers),
        args.country or "ES+DE",
    )

    # Run scrapers in parallel
    all_products: list[ProductPrice] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_scraper, s): s for s in scrapers}
        for future in as_completed(futures):
            products = future.result()
            all_products.extend(products)
            logger.info(
                "  ✓ %s → %d products",
                futures[future].retailer,
                len(products),
            )

    logger.info("Total products scraped: %d", len(all_products))

    if not all_products:
        logger.warning("No products found — check network connectivity or site structure changes.")
        return 1

    # Match and annotate compliance
    all_products = annotate_compliance(all_products)

    # Print console summary
    print_console_summary(all_products)

    # Save reports
    output_dir = Path(args.output)
    if not args.no_excel:
        excel_path = save_excel(all_products, output_dir)
        print(f"  Excel → {excel_path}")
    if not args.no_csv:
        csv_path = save_csv(all_products, output_dir)
        print(f"  CSV   → {csv_path}")
    if not args.no_json:
        json_path = save_json(all_products, output_dir)
        print(f"  JSON  → {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
