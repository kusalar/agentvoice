"""
catalogue.py — Live product catalogue lookup for the Local Commerce Assistant.

DATA SOURCE:
  Primary  : Open Food Facts API (https://world.openfoodfacts.org/api/v2)
             Free, no authentication required, real-time global food product data.
  Fallback : Hand-built local dataset (LOCAL_CATALOGUE) used when the API is
             unreachable (timeout, network error, rate-limit).

The tool always tells the caller when the data was fetched so they know
whether they're hearing a live price or a cached/static one.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("catalogue")

# ---------------------------------------------------------------------------
# Hand-built local fallback catalogue
# Used when the Open Food Facts API is unreachable.
# Prices are illustrative for the Indian local-commerce context.
# ---------------------------------------------------------------------------
LOCAL_CATALOGUE: list[dict[str, Any]] = [
    {
        "name": "Fresh Organic Wildflower Honey (500 g)",
        "price_inr": 450,
        "price_usd": 5.99,
        "vendor": "Local Apiary Farms",
        "stock": "In Stock",
        "description": "Pure, raw, 100% natural organic honey",
        "category": "honey",
    },
    {
        "name": "Handcrafted Sourdough Bread (750 g)",
        "price_inr": 220,
        "price_usd": 2.99,
        "vendor": "Artisan Local Bakery",
        "stock": "Baked Fresh Daily",
        "description": "Naturally fermented sourdough loaf",
        "category": "bread",
    },
    {
        "name": "Artisanal Roasted Coffee Beans (250 g)",
        "price_inr": 580,
        "price_usd": 7.50,
        "vendor": "Mountain Roast Co.",
        "stock": "In Stock",
        "description": "Single-origin medium roast, whole bean or ground",
        "category": "coffee",
    },
    {
        "name": "Handmade Ceramic Tea Mug (350 ml)",
        "price_inr": 350,
        "price_usd": 4.50,
        "vendor": "Heritage Pottery Crafts",
        "stock": "Limited Stock",
        "description": "Hand-painted pottery mug",
        "category": "mug",
    },
    {
        "name": "Organic Cold-Pressed Coconut Oil (1 Litre)",
        "price_inr": 650,
        "price_usd": 8.25,
        "vendor": "Green Harvest Organics",
        "stock": "In Stock",
        "description": "Pure unrefined extra virgin coconut oil",
        "category": "oil",
    },
    {
        "name": "Handwoven Cotton Tote Bag",
        "price_inr": 399,
        "price_usd": 4.99,
        "vendor": "EcoWeave Local",
        "stock": "In Stock",
        "description": "100% eco-friendly organic cotton bag",
        "category": "bag",
    },
]

# Keywords mapped to catalogue entries for local fuzzy matching
_KEYWORD_MAP: dict[str, int] = {
    "honey": 0,
    "wildflower": 0,
    "bread": 1,
    "sourdough": 1,
    "coffee": 2,
    "beans": 2,
    "roast": 2,
    "mug": 3,
    "ceramic": 3,
    "tea": 3,
    "coconut": 4,
    "oil": 4,
    "tote": 5,
    "bag": 5,
    "cotton": 5,
}


def _utc_now_readable() -> str:
    """Return current UTC time as a human-readable string."""
    now = datetime.now(timezone.utc)
    return now.strftime("%d %b %Y, %H:%M UTC")


def _local_search(query: str) -> dict[str, Any] | None:
    """Search the local fallback catalogue by keyword matching."""
    q = query.lower()
    for keyword, idx in _KEYWORD_MAP.items():
        if keyword in q:
            return LOCAL_CATALOGUE[idx]
    # Last resort: check if query matches any product name partially
    for item in LOCAL_CATALOGUE:
        if q in item["name"].lower() or item["name"].lower() in q:
            return item
    return None


async def fetch_product_from_api(query: str) -> dict[str, Any]:
    """
    Search Open Food Facts API for a product matching `query`.

    Returns a dict with keys:
        source       : "live" | "local_fallback"
        fetched_at   : human-readable UTC timestamp (always present)
        name         : product name
        brand        : brand or vendor
        category     : product category tags (from API) or local category
        quantity     : pack size / quantity string
        ingredients  : short ingredients summary (API only)
        stock        : stock status string
        price_inr    : price in INR (local catalogue value when live)
        price_usd    : price in USD (local catalogue value when live)
        api_error    : error message if API failed (absent on success)
        note         : human-readable data freshness note

    The Open Food Facts API is public and requires no API key.
    Endpoint: https://world.openfoodfacts.org/cgi/search.pl
    """
    try:
        import httpx  # imported lazily so missing dep gives clear error
    except ImportError:
        logger.error("httpx is not installed. Run: uv add httpx")
        return _build_fallback(query, "httpx library not installed. Using local data.")

    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 1,
        "fields": "product_name,brands,categories_tags,quantity,ingredients_text",
    }

    fetched_at = _utc_now_readable()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        products = data.get("products", [])
        if not products:
            logger.info(f"Open Food Facts returned 0 results for '{query}'. Using local fallback.")
            return _build_fallback(
                query,
                f"No matching product found in the live catalogue for '{query}'. Using local data.",
                fetched_at=fetched_at,
            )

        product = products[0]
        name = product.get("product_name") or query
        brand = product.get("brands") or "Unknown Brand"
        categories_raw = product.get("categories_tags") or []
        # Strip "en:" prefix from category tags, take first readable one
        categories = [
            c.replace("en:", "").replace("-", " ")
            for c in categories_raw
            if ":" not in c.replace("en:", "x", 1)
        ]
        category_str = ", ".join(categories[:3]) if categories else "food product"
        quantity = product.get("quantity") or "See packaging"
        ingredients_raw = product.get("ingredients_text") or ""
        # Truncate long ingredient lists for spoken delivery
        ingredients = ingredients_raw[:120].strip() + (
            "..." if len(ingredients_raw) > 120 else ""
        )

        # Try to match a local price for this product type
        local_match = _local_search(query)
        price_inr = local_match["price_inr"] if local_match else "Not listed"
        price_usd = local_match["price_usd"] if local_match else "Not listed"
        stock = local_match["stock"] if local_match else "Check with vendor"

        logger.info(
            f"Open Food Facts live hit for '{query}': '{name}' by '{brand}'"
        )
        return {
            "source": "live",
            "fetched_at": fetched_at,
            "name": name,
            "brand": brand,
            "category": category_str,
            "quantity": quantity,
            "ingredients": ingredients if ingredients else "Not listed",
            "stock": stock,
            "price_inr": price_inr,
            "price_usd": price_usd,
            "note": (
                f"Product details fetched live from Open Food Facts at {fetched_at}. "
                "Prices are from our local store catalogue."
            ),
        }

    except httpx.TimeoutException:
        logger.warning(
            f"Open Food Facts API timed out for query '{query}'. Using local fallback."
        )
        return _build_fallback(
            query,
            "The live catalogue is taking too long to respond right now. "
            "I'm using our local store data instead.",
            fetched_at=fetched_at,
        )
    except httpx.HTTPStatusError as e:
        logger.warning(
            f"Open Food Facts HTTP error {e.response.status_code} for '{query}'. "
            "Using local fallback."
        )
        return _build_fallback(
            query,
            f"The live catalogue returned an error (HTTP {e.response.status_code}). "
            "Using local data.",
            fetched_at=fetched_at,
        )
    except Exception as e:
        logger.warning(
            f"Open Food Facts unexpected error for '{query}': {e}. Using local fallback."
        )
        return _build_fallback(
            query,
            "The live catalogue is temporarily unavailable. Using local store data.",
            fetched_at=fetched_at,
        )


def _build_fallback(
    query: str,
    api_error: str,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    """Build a response from the local fallback catalogue."""
    if fetched_at is None:
        fetched_at = _utc_now_readable()

    local_match = _local_search(query)
    if local_match:
        return {
            "source": "local_fallback",
            "fetched_at": fetched_at,
            "name": local_match["name"],
            "brand": local_match["vendor"],
            "category": local_match["category"],
            "quantity": "See product label",
            "ingredients": local_match["description"],
            "stock": local_match["stock"],
            "price_inr": local_match["price_inr"],
            "price_usd": local_match["price_usd"],
            "api_error": api_error,
            "note": (
                f"Live catalogue unavailable. Showing local store data "
                f"(last verified: {fetched_at})."
            ),
        }

    # Nothing found at all — honest empty response
    return {
        "source": "local_fallback",
        "fetched_at": fetched_at,
        "name": None,
        "brand": None,
        "category": None,
        "quantity": None,
        "ingredients": None,
        "stock": "Unknown",
        "price_inr": None,
        "price_usd": None,
        "api_error": api_error,
        "note": (
            f"No information found for '{query}' in either the live catalogue "
            f"or local store data (checked at {fetched_at})."
        ),
    }
