# 🍊 Swiggy Proactive Ordering Agent

> **Built for Swiggy's Builders Club (MCP Developer Program)**  
> *A high-fidelity agentic framework designed to proactively draft food and grocery orders based on real-time user intents, weather triggers, and consumption replenishment predictions.*

---

## 🚀 The Pitch
Placing orders is reactive and induces choice fatigue. The **Swiggy Proactive Ordering Agent** acts as an invisible personal coordinator. By running background analyses on order history patterns, local weather, and dairy/staple consumption rates, it predicts when you are hungry or about to run out of staples and **prepares a draft cart ready for checkout**.

---

## 🎯 Dual Intelligent Trigger Engines

The system utilizes two independent background trigger engines, choreographed using **LangGraph**:

### 1. Event-Based Trigger (Food & Diners)
- **Temporal Windows**: Recognizes recurring ordering windows (e.g., Friday evenings).
- **Weather Compatibility**: Interfaces with local weather (rainy, hot, pleasant, cold). If the current weather matches the weather seen in **$\ge 60\%$ of past orders** inside that specific time window, the agent triggers.
- **Deduplication**: Suppressed if a Swiggy order was already placed on the same day.

### 2. Consumption-Based Trigger (Instamart Replenishment)
- **Zero Surveillance candidate matching**: Any item purchased $2+$ times is marked as a candidate staple.
- **Opt-In Confirmation**: The agent asks the user **exactly once** in the UI to opt-in for alerts. Only confirmed staples are actively tracked.
- **Habit-Adapting Rolling Average**: Instead of an all-time average, it calculates the **rolling average of the last 5 order gaps** as the consumption frequency.
- **Proactive Buffer**: Predicts the next depletion date and automatically drafts a replenishment cart **2 days before** the predicted run-out date.

---

## 🔀 Merge Logic & Safety First

- **Unified Notifications**: If both the event trigger and staple replenishment engines fire on the same day, they are **automatically merged into a single Daily Digest** to avoid notification fatigue.
- **Strictly Draft Carts**: The agent **NEVER auto-places an order**. Orders are drafted as inactive carts. The user must explicitly press **Confirm**, **Edit**, or **Dismiss**.
- **Dismissal Learning**: If a user dismisses a particular pattern or staple suggestion $3$ times, the agent **permanently stops suggesting it** to maintain trust.

---

## 🚧 Swiggy Platform Constraints Engineered Around

As a robust Builders Club submission, this codebase is engineered precisely around real-world Swiggy API limitations:
1. **No Pre-Order Prep-Time/ETA Endpoint**: The agent relies exclusively on Swiggy's `deliveryTimeRange` (e.g., `"25-35 MIN"`) display estimates returned by `search_restaurants` for pre-order states. Live ETAs are only available via post-order tracking endpoints.
2. **Strict Single-Restaurant Carts**: Food carts bind strictly to a single restaurant. `update_food_cart` automatically flushes existing items if a menu item from a different restaurant is added.
3. **No Scheduled Delivery Support**: Swiggy dispatches instantly. The agent only triggers instant, immediate-delivery drafts.
4. **Distance Guardrails**: `search_restaurants` exposes restaurant distances. In accordance with Swiggy API guardrails, the agent flashes a warning in the UI if a drafted restaurant is $>5\text{ km}$ away.
5. **Builders Club Sandbox Limits**: Sandboxed Builders Club accounts are restricted to **Cash on Delivery (COD)** payment types and a **₹1000 cart cap**. These validation guardrails are strictly checked in our mock MCP server before checkout.

---

## 🧪 Project Structure

```
swiggy-proactive-agent/
├── README.md               # Master pitch, features, and quickstart guide
├── architecture.md         # Extended architecture specification
├── requirements.txt        # Python package declarations
├── .env.example            # Environment variables template
├── src/
│   ├── main.py             # FastAPI entry point & API endpoints
│   ├── agents/
│   │   ├── event_trigger.py       # LangGraph event-based predictor
│   │   └── consumption_trigger.py # LangGraph staple consumption predictor
│   ├── mcp_client/
│   │   ├── base_client.py  # Abstract Client interface contract
│   │   ├── mock_client.py  # Schema-accurate Mock MCP Client
│   │   └── swiggy_client.py# Stubbed Real Swiggy Builders Club client
│   ├── scheduler/
│   │   └── daily_check.py  # Daily APScheduler simulation coordinator
│   ├── db/
│   │   ├── db.py           # SQLite connection and migration setup
│   │   └── models.py       # Pydantic data schemas
│   └── weather/
│       └── weather_client.py # OpenWeatherMap bucket coordinator
├── ui/
│   └── app.py              # Streamlit Interactive Dashboard Demo
├── tests/
│   └── test_trigger_logic.py # Pytest unit testing suite
└── demo/
    └── seed_data.py        # SQLite history pattern seeder
```

---

## 🏁 Quickstart Guide

### 1. Set Up Environment
```bash
# Clone the repository and navigate in
cd swiggy-proactive-agent

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the dependencies
pip install -r requirements.txt
```

### 2. Seed Database
Seed high-fidelity Friday-Biryani and 4-day Milk replenishment patterns in SQLite:
```bash
python -m demo.seed_data
```

### 3. Run Unit Tests
Verify the LangGraph state engines and rolling average calculators:
```bash
pytest tests/
```

### 4. Launch FastAPI API Server
```bash
uvicorn src.main:app --reload --port 8000
```

### 5. Launch Streamlit UI
In a separate terminal (with virtual environment active):
```bash
streamlit run ui/app.py
```

---

## ⚠️ Sandbox Notice
*This project is built against a mocked MCP layer matching Swiggy's real documented tool schemas pending production API credentials. Changing from sandbox mock to live production Swiggy API requires no code changes; simply swap the Client instantiation from `MockSwiggyMCPClient` to `RealSwiggyMCPClient` in `src/main.py`.*
