from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from src.db.db import get_connection, get_pattern_dismissal

class EventTriggerState(TypedDict):
    current_time: datetime
    weather: str
    lat: float
    lng: float
    order_history: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]

def analyze_patterns_node(state: EventTriggerState) -> Dict[str, Any]:
    """
    Analyzes historical order patterns to see if the current day/time and weather
    constitute a predictable ordering window.
    """
    curr_time = state["current_time"]
    curr_day = curr_time.weekday()
    curr_hour = curr_time.hour
    curr_weather = state["weather"]
    
    # 1. Guardrail: Check if we already ordered today
    # To check this, look at order_history for items ordered on the same calendar day
    curr_date_str = curr_time.date().isoformat()
    already_ordered = False
    for order in state["order_history"]:
        order_date = datetime.fromisoformat(order["order_time"]).date().isoformat()
        if order_date == curr_date_str:
            already_ordered = True
            break
            
    if already_ordered:
        print("[EVENT TRIGGER] Order already placed today. Skipping.")
        return {"suggestions": []}

    # 2. Find historical orders within the same Day of Week and Hour Window (+/- 2 hours)
    matching_past_orders = []
    for order in state["order_history"]:
        # Only look at past food orders
        if order["order_type"] != "food":
            continue
            
        o_dt = datetime.fromisoformat(order["order_time"])
        # Same weekday
        if o_dt.weekday() == curr_day:
            # Within +/- 2 hour window
            if abs(o_dt.hour - curr_hour) <= 2:
                matching_past_orders.append(order)

    # We need a minimum threshold of past orders to establish a robust pattern (e.g., >= 3 orders)
    min_orders_for_pattern = 3
    if len(matching_past_orders) < min_orders_for_pattern:
        print(f"[EVENT TRIGGER] Insufficient matching past orders ({len(matching_past_orders)} found, need {min_orders_for_pattern}).")
        return {"suggestions": []}

    # 3. Weather compatibility check: Do >= 60% of past orders in this window match current weather?
    weather_counts = {}
    for order in matching_past_orders:
        w = order["weather_condition"]
        weather_counts[w] = weather_counts.get(w, 0) + 1

    matching_weather_count = weather_counts.get(curr_weather, 0)
    weather_percentage = matching_weather_count / len(matching_past_orders)

    if weather_percentage < 0.60:
        print(f"[EVENT TRIGGER] Weather condition '{curr_weather}' does not match historical frequency ({weather_percentage:.1%} < 60%).")
        return {"suggestions": []}

    # 4. Extract most common restaurant and items ordered in this window
    restaurant_id = matching_past_orders[0]["restaurant_id"]
    restaurant_name = matching_past_orders[0]["restaurant_name"]
    
    # Aggregate items ordered in this window
    item_aggregation = {}
    for order in matching_past_orders:
        item_id = order["item_id"]
        if item_id not in item_aggregation:
            item_aggregation[item_id] = {
                "name": order["item_name"],
                "price": order["price"],
                "total_quantity": 0,
                "order_count": 0
            }
        item_aggregation[item_id]["total_quantity"] += order["quantity"]
        item_aggregation[item_id]["order_count"] += 1

    # Take items ordered in >= 50% of these window orders
    selected_items = []
    for item_id, details in item_aggregation.items():
        if details["order_count"] / len(matching_past_orders) >= 0.5:
            avg_qty = round(details["total_quantity"] / details["order_count"])
            selected_items.append({
                "item_id": item_id,
                "name": details["name"],
                "price": details["price"],
                "quantity": max(1, avg_qty)
            })

    if not selected_items:
        return {"suggestions": []}

    # 5. Dismissal Safety Guardrail: Check if user has dismissed this pattern 3+ times
    # Pattern key format: food_event_{day_of_week}_{hour_bucket}
    hour_bucket = f"{(curr_hour // 3) * 3}-{(curr_hour // 3) * 3 + 3}"
    day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][curr_day]
    pattern_key = f"food_event_{day_name}_{hour_bucket}"
    
    dismissal = get_pattern_dismissal(pattern_key)
    if dismissal and dismissal["dismissed_count"] >= 3:
        print(f"[EVENT TRIGGER] Pattern '{pattern_key}' ignored due to high dismissal count ({dismissal['dismissed_count']}).")
        return {"suggestions": []}

    # Fired! Calculate total and generate suggestion dict
    total_amount = sum(item["price"] * item["quantity"] for item in selected_items)
    
    suggestion = {
        "trigger_type": "event_based",
        "order_type": "food",
        "restaurant_id": restaurant_id,
        "restaurant_name": restaurant_name,
        "items": selected_items,
        "total_amount": total_amount,
        "explanation": f"Based on your past orders on {day_name}s around {curr_hour}:00 and today's {curr_weather} weather, you might want your favorite meal from {restaurant_name}!",
        "pattern_key": pattern_key
    }

    return {"suggestions": [suggestion]}

# Define the LangGraph workflow
workflow = StateGraph(EventTriggerState)

# Add Nodes
workflow.add_node("analyze_patterns", analyze_patterns_node)

# Set entry point
workflow.set_entry_point("analyze_patterns")

# Compile graph
event_trigger_graph = workflow.compile()

def run_event_trigger(current_time: datetime, weather: str, lat: float, lng: float, order_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Runs the LangGraph event-trigger flow and returns suggestions."""
    initial_state = {
        "current_time": current_time,
        "weather": weather,
        "lat": lat,
        "lng": lng,
        "order_history": order_history,
        "suggestions": []
    }
    result = event_trigger_graph.invoke(initial_state)
    return result.get("suggestions", [])
