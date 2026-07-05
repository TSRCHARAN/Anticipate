# 🏗️ Proactive Ordering Agent Architecture

This document describes the design, data schemas, and agent orchestrations for the Swiggy Builders Club Proactive Ordering Agent.

---

## 🗺️ Architectural Diagram

```
                 +-----------------------------------------+
                 |       APScheduler / UI Simulation       |
                 +--------------------+--------------------+
                                      |
                                      v (daily cron check)
                 +--------------------+--------------------+
                 |                FastAPI                  |
                 +----------+-------------------+----------+
                            |                   |
                            v                   v
            +---------------+---------------+   +---------------+---------------+
            |  LangGraph Event Trigger Agent |   | LangGraph Consumption Agent  |
            +---------------+---------------+   +---------------+---------------+
                            |                                   |
                            | (analyses history & weather)      | (computes rolling gaps)
                            +-------------------+---------------+
                                                |
                                                v
                                 +--------------+--------------+
                                 |         Merge Logic         |
                                 +--------------+--------------+
                                                |
                                                v (draft order recommendations)
                                 +--------------+--------------+
                                 |         Streamlit UI        |
                                 +--------------+--------------+
                                                |
                                                v (calls base interface)
                                 +--------------+--------------+
                                 |    BaseSwiggyMCPClient      |
                                 +--------------+--------------+
                                                |
                                   +------------+------------+
                                   |                         |
                                   v                         v
                       +-----------+-----------+ +-----------+-----------+
                       |  MockSwiggyMCPClient  | |  RealSwiggyMCPClient  |
                       +-----------------------+ +-----------------------+
```

---

## 🛠️ Multi-Agent Orchestration Flow (LangGraph)

Instead of traditional static checks, the system orchestrates triggers using **LangGraph**. This provides deterministic state validation and clean error isolation.

### 1. Event-Based Trigger Agent
- **Node 1: Pattern Analyzer (`analyze_patterns_node`)**:
  - Pulls order history from SQLite.
  - Groups past restaurant orders into temporal windows (same day of week, hour +/- 2 hours).
  - Fetches weather conditions and calculates historical frequency.
  - **Constraint Guard**: Asserts the weather bucket matches what was seen in $\ge 60\%$ of past orders in that window.
  - **Safety Guard**: Verifies no order has already been placed today.
  - **Trust Guard**: Confirms the pattern key (e.g., `food_event_Friday_18-21`) has not been dismissed 3+ times.
- **Node 2: Draft Suggester (`generate_food_draft_node`)**:
  - Constructs a single-restaurant draft cart.
  - Packages the suggestion with a clear natural language reasoning string (explanation).

### 2. Consumption-Based Staple Replenishment Agent
- **Node 1: Candidate Identifier (`process_consumption_node` - step 1)**:
  - Scans grocery histories and automatically flags any Instamart product ordered 2+ times.
  - Adds them to SQLite as "candidates". Displays an opt-in prompt in the UI (Hybrid Confirmation).
- **Node 2: Cycle Calculator (`process_consumption_node` - step 2)**:
  - Retrieves order dates for opted-in staples.
  - Sorts them chronologically and calculates day gaps between successive orders.
  - Computes a **rolling average of the last 5 gaps** (not all-time) to instantly adapt to changing habits.
- **Node 3: Predictor (`process_consumption_node` - step 3)**:
  - Computes `predicted_next_order = last_order_date + cycle_length`.
  - Fires a draft suggestion when `today >= predicted_next_order - 2 days` (buffer).

---

## 🔗 Platform-Safe Integration Interface

A key architectural highlight is the **`BaseSwiggyMCPClient`** abstraction. It mirrors Swiggy's actual Builders Club MCP tool schemas:

```python
class BaseSwiggyMCPClient(ABC):
    @abstractmethod
    def search_restaurants(self, lat: float, lng: float, query: Optional[str] = None) -> List[Dict[str, Any]]: ...
    @abstractmethod
    def update_food_cart(self, restaurant_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]: ...
    @abstractmethod
    def place_food_order(self, restaurant_id: str, items: List[Dict[str, Any]], payment_method: str = "COD") -> Dict[str, Any]: ...
    @abstractmethod
    def track_food_order(self, order_id: str) -> Dict[str, Any]: ...
```

This clean boundary guarantees that transitioning from the mock sandbox to the production Swiggy MCP server later requires **zero changes** in the agent orchestration and scheduler layers.

---

## 🗄️ Relational SQLite Data Models

The SQLite database (`src/db/swiggy_proactive.db`) manages three essential relational models:

```sql
-- Historical logs of user orders
CREATE TABLE order_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_type TEXT NOT NULL,         -- 'food' or 'instamart'
    restaurant_id TEXT,               -- null for instamart
    restaurant_name TEXT,
    item_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    order_time TEXT NOT NULL,         -- ISO format timestamp
    day_of_week INTEGER NOT NULL,     -- 0-6 (Monday-Sunday)
    hour INTEGER NOT NULL,            -- 0-23
    weather_condition TEXT NOT NULL   -- 'rainy', 'hot', 'pleasant', 'cold'
);

-- Opt-in, average cycles, and safety metrics for groceries
CREATE TABLE staple_config (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    is_confirmed INTEGER DEFAULT 0,    -- 0: candidate, 1: confirmed opt-in
    dismissed_count INTEGER DEFAULT 0, -- Auto-disabled if >= 3
    last_suggested_date TEXT,
    cycle_length REAL                  -- rolling average gap in days
);

-- Event pattern dismissal tracking
CREATE TABLE pattern_dismissals (
    pattern_key TEXT PRIMARY KEY,      -- e.g. 'food_event_Friday_18-21'
    dismissed_count INTEGER DEFAULT 0,  -- Disabled if >= 3
    last_dismissed_date TEXT
);
```
