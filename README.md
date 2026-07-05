# Anticipate — Proactive Ordering Agent

A proactive ordering agent built for Swiggy's Builders Club, using two independent
prediction engines to draft orders *before* the user asks — never auto-placing,
always requiring explicit confirmation.

## The Problem

Most ordering experiences are reactive — you open the app, decide, then order.
This project explores the opposite: can an agent notice patterns well enough to
draft the right order at the right moment, while staying fully transparent and
under user control?

## How It Works

### Trigger 1: Event-based prediction
Combines order history + weather + day-of-week to detect conditions matching a
past ordering pattern (e.g. "rainy Friday evenings → usual comfort food order").

### Trigger 2: Consumption-based replenishment
Tracks per-item reorder cycles for Instamart staples (milk, eggs, etc.) using a
rolling average of recent order gaps, and drafts a restock suggestion just before
predicted depletion. Tracking is **opt-in per item** — an item becomes a tracked
staple only after appearing in 2+ orders *and* explicit user confirmation, to
avoid silently monitoring everything a user buys.

### Safety by design
- The agent only ever builds a draft cart — `place_food_order` fires exclusively
  on explicit user confirmation
- Repeated dismissals of the same pattern suppress future suggestions for it
- Same-day triggers from both engines merge into a single suggestion instead of
  stacking notifications

## Platform Constraints Engineered Around

Swiggy's MCP tools don't expose several things a naive design might assume exist:

- **No pre-order ETA/prep-time prediction** — only a display-level
  `deliveryTimeRange` (e.g. "25-35 MIN") from `search_restaurants`
- **No shared/multi-restaurant cart** — `update_food_cart` is strictly bound to
  one restaurant; switching restaurants flushes the cart
- **No scheduled/future delivery** — orders are immediate-only
- **No delivery-partner or routing control** — dispatch is fully automatic and
  not exposed via API
- Live ETA is only available **after** an order is placed, via `track_food_order`
  polling (10s cadence)

This project is scoped to what's actually controllable given these constraints:
**order-placement timing**, not logistics.

## Architecture
[Order History + Weather + Calendar] → Event Trigger Engine (LangGraph)
[Instamart Order History]            → Consumption Trigger Engine (LangGraph)
↓                              ↓
[Merge Layer] → Draft Cart → React UI (Confirm / Edit / Dismiss)
↓
place_food_order (on confirm only)

## Tech Stack

- **Backend:** FastAPI, LangGraph (trigger orchestration), APScheduler (daily
  trigger checks), SQLite (order history, staple opt-ins, dismissals)
- **Frontend:** Vite + React (draft review UI)
- **MCP layer:** Mocked, matching Swiggy's documented tool schemas
  (`search_restaurants`, `update_food_cart`, `place_food_order`,
  `track_food_order`, Instamart equivalents), since production API access is
  pending. Client is built behind an abstract interface so swapping the mock
  for the real MCP client requires no logic changes.

## Running Locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

## Status

Built and tested against a mocked MCP layer pending Swiggy Builders Club
production access.



