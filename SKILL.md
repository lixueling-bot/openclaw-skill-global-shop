---
name: global-shop
description: Global shopping comparison and ordering skill. Trigger whenever a user expresses purchase intent — phrases like "help me buy", "find me the best price on", "where can I get", "shop for", "compare prices for", "帮我买", "想买", "全球搜索", "比价" all apply. Supports searching Amazon, eBay, Walmart, Temu, Etsy, and AliExpress; aggregates results and shows the 3–5 best options as visual cards with images, price+shipping totals, ratings, and a Best Value badge. User selects, then is directed to the platform to complete purchase. AI never touches payment passwords or CVV.
---

# Global Shop — 全球购物比价与下单

## Core Principles

**User drives decisions**: AI searches and filters; user makes the final choice and confirms. AI never places orders autonomously, never stores CVV, never touches payment passwords.

## Workflow

```
User expresses purchase intent (English or Chinese)
    ↓
Parse product keywords (supports EN/ZH, brand names, model numbers)
    ↓
Concurrently search all platforms
    ↓
Aggregate & deduplicate → score by (price + rating + shipping + reviews)
    ↓
Display 3–5 best options as cards (image, price+shipping total, rating, Best Value badge)
    ↓
User selects [A/B/C...]
    ↓
Redirect user to platform page to complete purchase
    ↓
User completes payment on platform (AI does not handle payment)
```

## Search Execution

Use `scripts/search.py` to concurrently search the following platforms:

| Platform | Search URL | Parser |
|----------|-----------|--------|
| Amazon | amazon.com/s?k={keyword} | parse_amazon.py |
| eBay | ebay.com/sch/i.html?_nkw={keyword} | parse_ebay.py |
| Walmart | walmart.com/search?q={keyword} | parse_walmart.py |
| Temu | temu.com/search_result.html?search_key={keyword} | parse_temu.py |
| Etsy | etsy.com/search?q={keyword} | parse_etsy.py |
| AliExpress | aliexpress.com/wholesale?SearchText={keyword} | parse_aliexpress.py |

**Language handling**: Automatically translate Chinese keywords to English for Western platforms. Etsy is best for handmade/vintage — only include it when the query seems relevant (gifts, crafts, unique items, vintage).

## Output Format — Cards Layout

Display results as visual cards, not a table. Each card includes:

```
🛍️ Best Results for: [search keyword]

┌─────────────────────────────────────────┐
│ [Product Image]        🏅 BEST VALUE    │  ← badge on top pick only
│ Platform: Walmart                        │
│ Product: [Name, truncated to ~60 chars] │
│ Price: $29.99  +  Shipping: $0.00       │
│ Estimated Total: $29.99                 │
│ Rating: ⭐ 4.7  (2,341 reviews)        │
│ Delivery: 2–3 days                      │
│ [View on Walmart →]                     │
└─────────────────────────────────────────┘
```

**Best Value badge** logic: Award to the card with the best combined score of (lowest estimated total) + (rating ≥ 4.0) + (delivery ≤ 7 days). Only one card gets the badge.

**Images**: Fetch the primary product thumbnail from each platform's search result and display inline above the product name.

**Estimated Total**: Always show price + shipping as a combined figure. If shipping is free, show "Shipping: FREE" and bold the total.

## Payment Flow

### Mode 1: Platform Account (default)
AI opens the target platform product page → user is already logged in → checks out using saved payment on platform.

### Mode 2: Credit Card (unified)
1. AI opens platform product page and fills in shipping address
2. AI opens credit card payment form (separate secure page)
3. User enters card number / expiry / name (CVV never saved)
4. User clicks "Confirm Payment"
5. Payment result shown

### Mode 3: Saved Card (optional)
- After first credit card entry, encrypted storage to `~/.qclaw/global-shop/cards.json`
- Future purchases: select saved card (only last 4 digits shown), enter CVV only
- User can say "delete saved cards" to clear all records

### Security Rules
- ❌ Never store CVV
- ❌ Never access payment passwords
- ❌ Never enter payment passwords outside the platform page
- ✅ All payments require explicit user confirmation
- ✅ `cards.json` encrypted at rest (AES-256)

## Platform Account Pre-storage

Users can optionally pre-store platform login info:
- Storage path: `~/.qclaw/global-shop/accounts.json` (encrypted)
- Supported: Amazon, eBay, Walmart, AliExpress, Etsy, Temu
- Usage: "buy this with my Amazon account" → use pre-stored credentials

## Common Commands

| User says | AI does |
|-----------|---------|
| "Help me buy AirPods" | Search → show cards → user picks → redirect |
| "帮我买 AirPods" | Same as above |
| "Cheapest iPhone anywhere" | Search all platforms, sort by estimated total |
| "Find this on Etsy" | Search Etsy only |
| "Only search Walmart and Amazon" | Restrict search to named platforms |
| "Use my saved card" | Load saved card list |
| "Delete saved cards" | Clear cards.json |
| "Add a platform account" | Guide user to add account info |

## Scripts

- `scripts/search.py` — concurrent search entry point, accepts keyword args
- `scripts/parse_*.py` — per-platform HTML parsers, output standardised JSON
- `scripts/rank.py` — multi-dimension scoring and ranking, emits Best Value winner
- `scripts/payment.py` — credit card encrypted storage and form filling
- `scripts/accounts.py` — platform account encrypted storage

See `references/platforms.md` and `references/payment.md` for detailed interface specs.
