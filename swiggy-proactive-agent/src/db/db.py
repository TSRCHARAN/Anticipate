import sqlite3
import os
from typing import List, Dict, Any, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "swiggy_proactive.db")

def get_connection():
    """Returns a SQLite connection and sets the row factory to access columns by name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if it doesn't already exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Table for past orders (hiring signal / historical trigger)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_type TEXT NOT NULL,         -- 'food' or 'instamart'
            restaurant_id TEXT,               -- rest_xxx (for food)
            restaurant_name TEXT,             -- Meghana Foods, etc.
            item_id TEXT NOT NULL,            -- m1, p1, etc.
            item_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            order_time TEXT NOT NULL,         -- ISO format: 2026-06-26T19:30:00
            day_of_week INTEGER NOT NULL,     -- 0 (Monday) to 6 (Sunday)
            hour INTEGER NOT NULL,            -- 0 to 23
            weather_condition TEXT NOT NULL   -- 'rainy', 'hot', 'pleasant', 'cold'
        )
    """)

    # 2. Table for Instamart Staples tracking configuration (Opt-in & Dismissals)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staple_config (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            is_confirmed INTEGER DEFAULT 0,    -- 0: pending opt-in, 1: confirmed opt-in
            dismissed_count INTEGER DEFAULT 0, -- Auto-disabled if >= 3
            last_suggested_date TEXT,
            cycle_length REAL                  -- rolling average gap in days
        )
    """)

    # 3. Table for Event-Based Pattern Dismissals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pattern_dismissals (
            pattern_key TEXT PRIMARY KEY,     -- e.g., 'food_event_Friday_evening'
            dismissed_count INTEGER DEFAULT 0, -- Auto-disabled if >= 3
            last_dismissed_date TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at {DB_PATH}")

# Helper operations for order histories
def get_all_order_history() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM order_history ORDER BY order_time DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_order_history(order_type: str, restaurant_id: Optional[str], restaurant_name: Optional[str],
                      item_id: str, item_name: str, price: float, quantity: int,
                      order_time: str, day_of_week: int, hour: int, weather_condition: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO order_history 
        (order_type, restaurant_id, restaurant_name, item_id, item_name, price, quantity, order_time, day_of_week, hour, weather_condition)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (order_type, restaurant_id, restaurant_name, item_id, item_name, price, quantity, order_time, day_of_week, hour, weather_condition))
    conn.commit()
    conn.close()

# Helper operations for Instamart staple opt-ins
def get_staple_config(product_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM staple_config WHERE product_id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_staple_configs() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM staple_config").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_staple_config(product_id: str, product_name: str, is_confirmed: int, dismissed_count: int, cycle_length: Optional[float] = None, last_suggested_date: Optional[str] = None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO staple_config (product_id, product_name, is_confirmed, dismissed_count, cycle_length, last_suggested_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(product_id) DO UPDATE SET
            is_confirmed = excluded.is_confirmed,
            dismissed_count = excluded.dismissed_count,
            cycle_length = COALESCE(excluded.cycle_length, staple_config.cycle_length),
            last_suggested_date = COALESCE(excluded.last_suggested_date, staple_config.last_suggested_date)
    """, (product_id, product_name, is_confirmed, dismissed_count, cycle_length, last_suggested_date))
    conn.commit()
    conn.close()

# Helper operations for Event-Based patterns
def get_pattern_dismissal(pattern_key: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM pattern_dismissals WHERE pattern_key = ?", (pattern_key,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_pattern_dismissal(pattern_key: str, dismissed_count: int, last_dismissed_date: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO pattern_dismissals (pattern_key, dismissed_count, last_dismissed_date)
        VALUES (?, ?, ?)
        ON CONFLICT(pattern_key) DO UPDATE SET
            dismissed_count = excluded.dismissed_count,
            last_dismissed_date = excluded.last_dismissed_date
    """, (pattern_key, dismissed_count, last_dismissed_date))
    conn.commit()
    conn.close()
