"""Price research for Etsy sellers: what do competing listings charge?

Give it the search phrases a buyer would type for your product. For each one it
reads the top listings and prints the price spread, how many are on sale or ship
free, and which shops dominate. Optionally it checks where your own price falls.

Usage:
    export APIFY_TOKEN=...
    python price_check.py "ceramic mug" "handmade ceramic mug" --top 40
    python price_check.py "leather wallet men" --my-price 45 --ships-to GB --currency GBP
    python price_check.py "soy candle" --csv listings.csv
"""

import argparse
import csv
import os
import sys
from decimal import Decimal

from apify_client import ApifyClient

ACTOR = "heyitsgautham/etsy-products-scraper"
PRICE_PER_PRODUCT = Decimal("0.001")
CSV_FIELDS = ["input", "position", "title", "price", "originalPrice", "discountPercent",
              "currency", "freeShipping", "shopName", "shopRating", "badges", "url"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("keywords", nargs="+", help="Etsy search phrases")
    parser.add_argument("--top", type=int, default=40, help="listings to sample per phrase (default 40)")
    parser.add_argument("--my-price", type=float, help="your price, to see where it ranks")
    parser.add_argument("--ships-to", help="two-letter country, e.g. US or GB")
    parser.add_argument("--currency", help="e.g. USD, GBP, EUR")
    parser.add_argument("--csv", help="also save every listing to this CSV")
    args = parser.parse_args()

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("Set APIFY_TOKEN first. Get one at https://console.apify.com/settings/integrations")

    run_input = {"searchQueries": args.keywords, "maxItems": args.top, "priceSummary": True}
    if args.ships_to:
        run_input["shipsTo"] = args.ships_to
    if args.currency:
        run_input["currency"] = args.currency
    cap = PRICE_PER_PRODUCT * args.top * len(args.keywords)
    print(f"Sampling {args.top} listings for {len(args.keywords)} phrases, at most ${cap:.3f}\n")

    client = ApifyClient(token)
    run = client.actor(ACTOR).call(run_input=run_input, max_total_charge_usd=cap, logger=None)
    if run is None or run.status != "SUCCEEDED":
        sys.exit(f"Run did not succeed: {run.status if run else 'no run'}")

    products, summaries = [], []
    for item in client.dataset(run.default_dataset_id).iterate_items():
        if item.get("status") == "ok":
            products.append(item)
        elif item.get("status") == "summary":
            summaries.append(item)
        else:
            print(f"Skipped {item.get('input')}: {item.get('status')}, {item.get('message')}")

    for s in summaries:
        cur = s["currency"]
        print(f"## {s['input']}  ({s['productCount']} listings, {s['shopCount']} shops)")
        print(f"  price      min {s['priceMin']:.2f}  25% {s['priceP25']:.2f}  median {s['priceMedian']:.2f}"
              f"  75% {s['priceP75']:.2f}  max {s['priceMax']:.2f} {cur}")
        print(f"  on sale    {s['onSalePercent']:.0f}%, median discount {s['medianDiscountPercent'] or 0:.0f}%")
        print(f"  ships free {s['freeShippingPercent']:.0f}%")
        top = [f"{t['shopName'] or '(hidden)'} x{t['listings']}" for t in (s.get("topShops") or [])[:3]]
        if top:
            print(f"  top shops  {', '.join(top)}")
        if args.my_price is not None:
            prices = [p["price"] for p in products if p.get("input") == s["input"] and p.get("price") is not None]
            cheaper = sum(price < args.my_price for price in prices)
            print(f"  your {args.my_price:.2f} is above {cheaper} of {len(prices)} listings")
        print()

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for p in products:
                writer.writerow({**p, "badges": "; ".join(p.get("badges") or [])})
        print(f"Saved {len(products)} listings to {args.csv}")


if __name__ == "__main__":
    main()
