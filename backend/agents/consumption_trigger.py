from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from db.db import get_all_staple_configs, update_staple_config

class ConsumptionTriggerState(TypedDict):
    current_time: datetime
    order_history: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    candidate_staples: List[Dict[str, Any]]  # items ordered 2+ times not yet opt-in

def process_consumption_node(state: ConsumptionTriggerState) -> Dict[str, Any]:
    """
    Scans order history, calculates rolling averages of gaps, registers candidates,
    and drafts replenishment orders for opted-in staples.
    """
    curr_time = state["current_time"]
    today_dt = curr_time.date()
    history = state["order_history"]
    
    # 1. Group Instamart order dates per item
    instamart_orders_by_product = {}
    for order in history:
        if order["order_type"] != "instamart":
            continue
        prod_id = order["item_id"]
        if prod_id not in instamart_orders_by_product:
            instamart_orders_by_product[prod_id] = {
                "name": order["item_name"],
                "price": order["price"],
                "dates": []
            }
        # Parse date
        dt = datetime.fromisoformat(order["order_time"]).date()
        if dt not in instamart_orders_by_product[prod_id]["dates"]:
            instamart_orders_by_product[prod_id]["dates"].append(dt)

    # 2. Identify candidate staples (ordered 2+ times, not yet in staple_config)
    candidate_staples = []
    configs = {c["product_id"]: c for c in get_all_staple_configs()}
    
    for prod_id, info in instamart_orders_by_product.items():
        if len(info["dates"]) >= 2:
            # Check if it exists in DB config
            if prod_id not in configs:
                # Calculate initial rough average gap
                sorted_dates = sorted(info["dates"])
                gaps = [(sorted_dates[i] - sorted_dates[i-1]).days for i in range(1, len(sorted_dates))]
                avg_gap = sum(gaps) / len(gaps) if gaps else 4.0
                
                # Register in database with is_confirmed = 0 (pending)
                update_staple_config(
                    product_id=prod_id,
                    product_name=info["name"],
                    is_confirmed=0,  # Not yet confirmed
                    dismissed_count=0,
                    cycle_length=avg_gap
                )
                
                candidate_staples.append({
                    "product_id": prod_id,
                    "product_name": info["name"],
                    "estimated_cycle": round(avg_gap, 1)
                })
            elif configs[prod_id]["is_confirmed"] == 0:
                # It is a registered candidate, but user hasn't opted in yet
                # Add to candidate list for UI prompt
                candidate_staples.append({
                    "product_id": prod_id,
                    "product_name": info["name"],
                    "estimated_cycle": round(configs[prod_id]["cycle_length"] or 4.0, 1)
                })

    # 3. Process confirmed staples
    suggestions = []
    buffer_days = 2  # Trigger draft when today >= predicted_next_order - 2 days
    
    for prod_id, config in configs.items():
        if config["is_confirmed"] == 1 and config["dismissed_count"] < 3:
            # Get historical orders for this product
            history_info = instamart_orders_by_product.get(prod_id)
            if not history_info or len(history_info["dates"]) < 2:
                continue
                
            sorted_dates = sorted(history_info["dates"])
            last_order_date = sorted_dates[-1]
            
            # Compute consecutive order gaps
            gaps = [(sorted_dates[i] - sorted_dates[i-1]).days for i in range(1, len(sorted_dates))]
            
            # Grab the LAST 5 gaps for rolling average (adapts to habit changes!)
            rolling_gaps = gaps[-5:]
            cycle_length = sum(rolling_gaps) / len(rolling_gaps) if rolling_gaps else 4.0
            
            # Sync updated cycle length to db
            update_staple_config(
                product_id=prod_id,
                product_name=config["product_name"],
                is_confirmed=1,
                dismissed_count=config["dismissed_count"],
                cycle_length=cycle_length,
                last_suggested_date=config["last_suggested_date"]
            )
            
            # Calculate prediction
            predicted_next_order = last_order_date + timedelta(days=cycle_length)
            days_until_due = (predicted_next_order - today_dt).days
            
            # Trigger draft suggestion if today matches prediction threshold
            if today_dt >= (predicted_next_order - timedelta(days=buffer_days)):
                # Guard: make sure we don't spam if suggested recently
                last_sug = config["last_suggested_date"]
                if last_sug and last_sug == today_dt.isoformat():
                    continue  # already suggested today
                    
                # Calculate replenishment quantity (average quantity of past orders)
                total_qty = 0
                order_count = 0
                for order in history:
                    if order["item_id"] == prod_id:
                        total_qty += order["quantity"]
                        order_count += 1
                avg_qty = max(1, round(total_qty / order_count) if order_count > 0 else 1)
                
                total_amount = history_info["price"] * avg_qty
                
                suggestions.append({
                    "trigger_type": "consumption_based",
                    "order_type": "instamart",
                    "product_id": prod_id,
                    "product_name": config["product_name"],
                    "items": [{
                        "product_id": prod_id,
                        "name": config["product_name"],
                        "price": history_info["price"],
                        "quantity": avg_qty
                    }],
                    "total_amount": total_amount,
                    "explanation": f"Looks like you are running low on your staple {config['product_name']}. Based on your last 5 orders, you replenish it every {round(cycle_length, 1)} days. Your next order is predicted on {predicted_next_order}.",
                    "pattern_key": f"instamart_replenish_{prod_id}"
                })

    return {
        "suggestions": suggestions,
        "candidate_staples": candidate_staples
    }

# Define the LangGraph workflow
workflow = StateGraph(ConsumptionTriggerState)
workflow.add_node("process_consumption", process_consumption_node)
workflow.set_entry_point("process_consumption")
consumption_trigger_graph = workflow.compile()

def run_consumption_trigger(current_time: datetime, order_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Runs the LangGraph consumption-trigger flow."""
    initial_state = {
        "current_time": current_time,
        "order_history": order_history,
        "suggestions": [],
        "candidate_staples": []
    }
    result = consumption_trigger_graph.invoke(initial_state)
    return {
        "suggestions": result.get("suggestions", []),
        "candidate_staples": result.get("candidate_staples", [])
    }
