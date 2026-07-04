import sys
import os
from datetime import datetime, timedelta

# Append src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.db.db import init_db, add_order_history, update_staple_config

def seed():
    print("[SEED] Starting database initialization and seeding...")
    init_db()

    # Clear previous entries to make it idempotent
    from src.db.db import get_connection
    conn = get_connection()
    conn.execute("DELETE FROM order_history")
    conn.execute("DELETE FROM staple_config")
    conn.execute("DELETE FROM pattern_dismissals")
    conn.commit()
    conn.close()

    # --- Pattern 1: Event-Based Friday Evening Biryani ---
    # Friday evenings in June 2026:
    # June 26, June 19, June 12, June 5
    # Let's seed 4 orders. Weather in 3 out of 4 orders is "rainy", making it 75% rainy (>= 60% threshold!)
    friday_orders = [
        {
            "order_time": "2026-06-26T19:30:00",
            "weather_condition": "rainy"
        },
        {
            "order_time": "2026-06-19T20:15:00",
            "weather_condition": "rainy"
        },
        {
            "order_time": "2026-06-12T19:45:00",
            "weather_condition": "rainy"
        },
        {
            "order_time": "2026-06-05T19:15:00",
            "weather_condition": "pleasant"
        }
    ]

    for order in friday_orders:
        dt = datetime.fromisoformat(order["order_time"])
        add_order_history(
            order_type="food",
            restaurant_id="rest_001",
            restaurant_name="Meghana Foods",
            item_id="m1",
            item_name="Special Chicken Biryani",
            price=320.0,
            quantity=1,
            order_time=order["order_time"],
            day_of_week=dt.weekday(),  # 4 for Friday
            hour=dt.hour,
            weather_condition=order["weather_condition"]
        )
    print("[SEED] Seeded 4 Friday evening food orders (Meghana Foods Biryani - rainy weather pattern).")

    # --- Pattern 2: Consumption-Based Staple Milk ---
    # Milk purchased every 4 days: June 16, June 20, June 24, June 28, July 2
    milk_orders = [
        "2026-06-16T08:00:00",
        "2026-06-20T08:30:00",
        "2026-06-24T08:15:00",
        "2026-06-28T09:00:00",
        "2026-07-02T08:10:00"
    ]

    for o_time in milk_orders:
        dt = datetime.fromisoformat(o_time)
        add_order_history(
            order_type="instamart",
            restaurant_id=None,
            restaurant_name=None,
            item_id="p1",
            item_name="Nandini Fresh Milk (500ml)",
            price=27.0,
            quantity=2,  # Ordered 2 of these
            order_time=o_time,
            day_of_week=dt.weekday(),
            hour=dt.hour,
            weather_condition="pleasant"
        )
    
    # Pre-add milk to the staple_config as confirmed, so trigger logic tracks it
    # Last order date is July 2, 2026. Cycle length is 4.0 days.
    update_staple_config(
        product_id="p1",
        product_name="Nandini Fresh Milk (500ml)",
        is_confirmed=1,  # User confirmed opt-in
        dismissed_count=0,
        cycle_length=4.0,
        last_suggested_date=None
    )

    # Let's also add Eggs "Fresh Eggs (Pack of 6)" as a CANDIDATE (ordered 2 times, but not yet confirmed!)
    # June 25, June 30 (ordered 2 times) -> candidate, user should be prompted to opt-in
    egg_orders = [
        "2026-06-25T08:30:00",
        "2026-06-30T08:45:00"
    ]
    for o_time in egg_orders:
        dt = datetime.fromisoformat(o_time)
        add_order_history(
            order_type="instamart",
            restaurant_id=None,
            restaurant_name=None,
            item_id="p2",
            item_name="Fresh Eggs (Pack of 6)",
            price=48.0,
            quantity=1,
            order_time=o_time,
            day_of_week=dt.weekday(),
            hour=dt.hour,
            weather_condition="pleasant"
        )

    print("[SEED] Seeded 5 milk orders (4-day cycle) and 2 egg orders (candidate staple).")
    print("[SEED] Seeding completed successfully!")

if __name__ == "__main__":
    seed()
