#!/usr/bin/env python3
"""
Helper to update official_prices.py from a CSV exported from Bover's price list.

CSV format expected:
  product_name,price
  "Bover Kata P/01",499.00
  "Bover Kata P/02",569.00
  ...

Usage:
  python update_prices.py bover_official_pricelist.csv
"""

import csv
import re
import sys
from pathlib import Path


def normalise(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^\w\s/]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python update_prices.py <prices.csv>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        sys.exit(1)

    entries: list[tuple[str, float]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("product_name", "").strip()
            try:
                price = float(row["price"])
            except (KeyError, ValueError):
                continue
            if name:
                entries.append((normalise(name), price))

    if not entries:
        print("No valid entries found in CSV.")
        sys.exit(1)

    # Generate the dict literal
    lines = ["OFFICIAL_PRICES: dict[str, float] = {"]
    for name, price in sorted(entries):
        lines.append(f'    "{name}": {price:.2f},')
    lines.append("}")

    out_path = Path("bover_scraper/official_prices_new.py")
    out_path.write_text(
        '"""Auto-generated from CSV. Replace the dict in official_prices.py."""\n\n'
        + "\n".join(lines)
        + "\nMAX_DISCOUNT_PCT: float = 15.0\n"
    )
    print(f"Generated {out_path} with {len(entries)} entries.")
    print("Review it and replace the OFFICIAL_PRICES dict in bover_scraper/official_prices.py")


if __name__ == "__main__":
    main()
