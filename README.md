# Etsy products scraper

Before I price something, I want to know what the listings next to it charge.
`price_check.py` answers that for any Etsy search phrase, from the command line.

It runs on my [Etsy Products & Listings Scraper](https://apify.com/heyitsgautham/etsy-products-scraper), a scraper I built on Apify.
It's paid per result, $1 per 1,000 products, and failed rows and price summaries are free.
You don't need an Etsy API key or an Etsy account.

## Price check

```bash
pip install -r requirements.txt
export APIFY_TOKEN=your_token_here
python price_check.py "soy candle" "beeswax candle" --top 25 --my-price 18 --csv listings.csv
```

Output from my run on 26 Oct 2026:

```
Sampling 25 listings for 2 phrases, at most $0.050

## beeswax candle  (25 listings, 24 shops)
  price      min 0.70  25% 10.74  median 16.00  75% 20.00  max 39.47 USD
  on sale    40%, median discount 20%
  ships free 32%
  top shops  (hidden) x2
  your 18.00 is above 15 of 25 listings

## soy candle  (25 listings, 22 shops)
  price      min 2.95  25% 11.65  median 12.90  75% 21.99  max 74.99 USD
  on sale    60%, median discount 30%
  ships free 12%
  top shops  TheThriftyWick x3, WispyWickCandles x2
  your 18.00 is above 18 of 25 listings

Saved 50 listings to listings.csv
```

So an $18 soy candle sits in the top third, and 60% of the competition is "on sale".
I'd watch the sale share more than the median, since most of those listings show a crossed-out higher price.

What each line means:

- The price spread is the current price, sale included, with quartiles worked out like Excel's `QUARTILE.INC`.
- "On sale" is the share of listings with a discount, and the median `% off` among them.
- "Ships free" is the share Etsy marks with free shipping to the ships-to country.
- "Top shops" lists shops with 2 or more listings in the sample. Keyword search cards sometimes hide the shop name, which shows as `(hidden)`.

`--ships-to GB --currency GBP` switches the whole check to what a UK buyer sees.
`--top` sets the sample size per phrase, and the script caps the run's charge at `--top` times the number of phrases times $0.001.

## The data under it

Each product comes back as one row.
This is the first beeswax candle from the run above.

```json
{
  "status": "ok",
  "input": "beeswax candle",
  "position": 1,
  "listingId": "1047360684",
  "title": "Organic Beeswax Candle (9oz): Scented Aromatherapy Candle",
  "url": "https://www.etsy.com/listing/1047360684/organic-beeswax-candle-9oz-scented",
  "price": 20.39,
  "isOnSale": true,
  "originalPrice": 23.99,
  "discountPercent": 15,
  "shopId": "11215001",
  "shopName": "beEsom",
  "shopRating": 4.9,
  "shopReviewCount": 7500,
  "freeShipping": true,
  "badges": ["Bestseller"],
  "shipsFrom": null,
  "isAd": false,
  "image": "https://i.etsystatic.com/11215001/r/il/accee7/3289014651/il_fullxfull.3289014651_etq2.jpg",
  "shopUrl": "https://www.etsy.com/shop/beEsom",
  "currency": "USD"
}
```

`shopRating` and `shopReviewCount` are shop-level, and Etsy rounds big counts, so 7.5k shows as 7500.
With `"priceSummary": true`, each phrase also gets one free `summary` row with those quartiles, which is what the script prints.

## Python, without the script

```python
import os
from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])
run = client.actor("heyitsgautham/etsy-products-scraper").call(run_input={
    "searchQueries": ["ceramic mug"],
    "startUrls": [{"url": "https://www.etsy.com/shop/CaitlynMinimalist"}],
    "maxItems": 100,
})
for row in client.dataset(run.default_dataset_id).iterate_items():
    print(row["status"], row.get("price"), row.get("title"))
```

## curl, straight to CSV

```bash
curl -X POST "https://api.apify.com/v2/acts/heyitsgautham~etsy-products-scraper/run-sync-get-dataset-items?format=csv&fields=position,title,price,currency,shopName,url" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"searchQueries": ["leather wallet men"], "maxItems": 3}' > wallets.csv
```

When I ran it, the first row was a $59.60 slim cash wallet from LeatherLabStudioCo.

## What it can read

| Input | Example |
|---|---|
| Keyword | `ceramic mug` |
| Search URL, filters kept | `https://www.etsy.com/search?q=boho+rug&min=50&max=200` |
| Category URL | `https://www.etsy.com/c/jewelry/necklaces` |
| Market URL | `https://www.etsy.com/market/ceramic_mug` |
| Shop URL | `https://www.etsy.com/shop/CaitlynMinimalist` |
| Listing URL or ID | `https://www.etsy.com/listing/1371848548` |

Locale URLs such as `etsy.com/uk/...` work too.
Filters for keywords, search, market and category pages are `minPrice`, `maxPrice`, `shipsTo`, `freeShipping`, `currency` and `sortBy`.

Turn on `includeDetails` for the description, all images, favorites, the listing's own rating and reviews, materials, stock and shipping cost.
That costs $3.40 per 1,000 extra, charged only when the details load.

## Price

| | No discount | Bronze | Silver | Gold |
|---|---|---|---|---|
| Per 1,000 products | $1 | $0.95 | $0.92 | $0.92 |
| Listing details, per 1,000 | $3.40 | $3.40 | $3.40 | $3.40 |
| Price summary rows, failed rows | Free | Free | Free | Free |

In the final test, 57 of 57 valid inputs returned products, and 700 products without details took 22 seconds.

## Limits

- Etsy's bot protection blocks some requests. The scraper retries on new residential IPs, which keeps failures rare but not zero. Failed rows are free.
- The tags a seller typed aren't on Etsy's public page. With details on, `relatedSearches` holds the search phrases Etsy links instead.
- Variation prices come as `price` (lowest) and `maxPrice` (highest), not per option.

## License

MIT for this repo's code.
