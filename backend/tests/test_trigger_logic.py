import sys
import os
from datetime import datetime, timedelta
import pytest

# Append src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from agents.event_trigger import run_event_trigger
from agents.consumption_trigger import run_consumption_trigger
from db.db import init_db, update_staple_config

@pytest.fixture(autouse=True)
def setup_test_db():
    """Initializes the SQLite schema for test isolation."""
    init_db()

def test_event_trigger_success_flow():
    """
    Tests that the event-based trigger fires correctly when:
    - Current day/time matches historical window (Friday evening).
    - Weather condition matches the >=60% frequency of historical orders (Rainy).
    """
    # 4 past Friday food orders (3 rainy, 1 pleasant => 75% rainy weather)
    mock_history = [
        {
            "order_type": "food",
            "restaurant_id": "rest_001",
            "restaurant_name": "Meghana Foods",
            "item_id": "m1",
            "item_name": "Special Chicken Biryani",
            "price": 320.0,
            "quantity": 1,
            "order_time": "2026-06-26T19:30:00",
            "weather_condition": "rainy"
        },
        {
            "order_type": "food",
            "restaurant_id": "rest_001",
            "restaurant_name": "Meghana Foods",
            "item_id": "m1",
            "item_name": "Special Chicken Biryani",
            "price": 320.0,
            "quantity": 1,
            "order_time": "2026-06-19T20:15:00",
            "weather_condition": "rainy"
        },
        {
            "order_type": "food",
            "restaurant_id": "rest_001",
            "restaurant_name": "Meghana Foods",
            "item_id": "m1",
            "item_name": "Special Chicken Biryani",
            "price": 320.0,
            "quantity": 1,
            "order_time": "2026-06-12T19:45:00",
            "weather_condition": "rainy"
        },
        {
            "order_type": "food",
            "restaurant_id": "rest_001",
            "restaurant_name": "Meghana Foods",
            "item_id": "m1",
            "item_name": "Special Chicken Biryani",
            "price": 320.0,
            "quantity": 1,
            "order_time": "2026-06-05T19:15:00",
            "weather_condition": "pleasant"
        }
    ]

    # Run check for Friday July 3, 2026 at 19:30, with rainy weather (Expected: Fires!)
    current_time = datetime.fromisoformat("2026-07-03T19:30:00")
    suggestions = run_event_trigger(
        current_time=current_time,
        weather="rainy",
        lat=12.9716,
        lng=77.5946,
        order_history=mock_history
    )

    assert len(suggestions) == 1
    assert suggestions[0]["restaurant_id"] == "rest_001"
    assert suggestions[0]["trigger_type"] == "event_based"
    assert "Special Chicken Biryani" in suggestions[0]["items"][0]["name"]

def test_event_trigger_weather_mismatch():
    """
    Tests that the event-based trigger is suppressed when the current weather
    does not match the historical threshold (60%).
    """
    mock_history = [
        {"order_type": "food", "restaurant_id": "rest_001", "restaurant_name": "Meghana Foods", "item_id": "m1", "item_name": "Special Chicken Biryani", "price": 320, "quantity": 1, "order_time": "2026-06-26T19:30:00", "weather_condition": "rainy"},
        {"order_type": "food", "restaurant_id": "rest_001", "restaurant_name": "Meghana Foods", "item_id": "m1", "item_name": "Special Chicken Biryani", "price": 320, "quantity": 1, "order_time": "2026-06-19T20:15:00", "weather_condition": "rainy"},
        {"order_type": "food", "restaurant_id": "rest_001", "restaurant_name": "Meghana Foods", "item_id": "m1", "item_name": "Special Chicken Biryani", "price": 320, "quantity": 1, "order_time": "2026-06-12T19:45:00", "weather_condition": "rainy"},
        {"order_type": "food", "restaurant_id": "rest_001", "restaurant_name": "Meghana Foods", "item_id": "m1", "item_name": "Special Chicken Biryani", "price": 320, "quantity": 1, "order_time": "2026-06-05T19:15:00", "weather_condition": "pleasant"}
    ]

    # Current weather is hot, whereas history was rainy (Expected: Suppressed)
    current_time = datetime.fromisoformat("2026-07-03T19:30:00")
    suggestions = run_event_trigger(
        current_time=current_time,
        weather="hot",
        lat=12.9716,
        lng=77.5946,
        order_history=mock_history
    )

    assert len(suggestions) == 0

def test_consumption_trigger_rolling_average():
    """
    Tests that the consumption-based trigger:
    - Identifies chronological gaps between staple orders.
    - Calculates a rolling average of the gaps.
    - Accurately triggers on the correct date with a 2-day buffer.
    """
    # Spaced exactly 4 days apart: June 16, 20, 24, 28, July 2
    mock_history = [
        {"order_type": "instamart", "item_id": "p1", "item_name": "Nandini Fresh Milk (500ml)", "price": 27.0, "quantity": 2, "order_time": "2026-06-16T08:00:00", "weather_condition": "pleasant"},
        {"order_type": "instamart", "item_id": "p1", "item_name": "Nandini Fresh Milk (500ml)", "price": 27.0, "quantity": 2, "order_time": "2026-06-20T08:00:00", "weather_condition": "pleasant"},
        {"order_type": "instamart", "item_id": "p1", "item_name": "Nandini Fresh Milk (500ml)", "price": 27.0, "quantity": 2, "order_time": "2026-06-24T08:00:00", "weather_condition": "pleasant"},
        {"order_type": "instamart", "item_id": "p1", "item_name": "Nandini Fresh Milk (500ml)", "price": 27.0, "quantity": 2, "order_time": "2026-06-28T08:00:00", "weather_condition": "pleasant"},
        {"order_type": "instamart", "item_id": "p1", "item_name": "Nandini Fresh Milk (500ml)", "price": 27.0, "quantity": 2, "order_time": "2026-07-02T08:00:00", "weather_condition": "pleasant"}
    ]

    # Pre-configure item in database as Opted-in (is_confirmed = 1)
    update_staple_config(
        product_id="p1",
        product_name="Nandini Fresh Milk (500ml)",
        is_confirmed=1,
        dismissed_count=0,
        cycle_length=4.0
    )

    # Next predicted is July 2 + 4 days = July 6.
    # With a 2-day buffer, it should start suggesting on July 4.
    
    # Check for July 3 (predicted = 6, buffer = 2 => starts trigger on 4th) (Expected: Should NOT trigger)
    res_july3 = run_consumption_trigger(
        current_time=datetime.fromisoformat("2026-07-03T12:00:00"),
        order_history=mock_history
    )
    assert len(res_july3["suggestions"]) == 0

    # Check for July 4 (Expected: Triggers)
    res_july4 = run_consumption_trigger(
        current_time=datetime.fromisoformat("2026-07-04T12:00:00"),
        order_history=mock_history
    )
    assert len(res_july4["suggestions"]) == 1
    assert res_july4["suggestions"][0]["product_id"] == "p1"
    assert res_july4["suggestions"][0]["trigger_type"] == "consumption_based"
