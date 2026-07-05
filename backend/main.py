import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from db.db import init_db, get_all_order_history, update_staple_config, get_staple_config, update_pattern_dismissal, get_pattern_dismissal, get_all_staple_configs
from mcp_client.mock_client import MockSwiggyMCPClient
from scheduler.daily_check import ProactiveDailyScheduler

app = FastAPI(
    title="Swiggy Proactive Ordering Agent - Builders Club",
    description="API layer of the proactive order suggestion system built with LangGraph, FastAPI, and SQLite."
)

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Instantiate the abstract-backed Swiggy MCP Client
# To swap this with the production MCP client in the future, simply swap this line:
# mcp_client = RealSwiggyMCPClient()
mcp_client = MockSwiggyMCPClient()

class StapleOptInRequest(BaseModel):
    product_id: str
    product_name: str
    confirm: bool

class DismissRequest(BaseModel):
    pattern_key: str
    is_staple: bool = False

class OrderRequest(BaseModel):
    order_type: str  # 'food' or 'instamart'
    restaurant_id: Optional[str] = None
    items: List[Dict[str, Any]]  # List of {"item_id"/"product_id": str, "quantity": int}
    payment_method: str = "COD"

@app.get("/api/health")
def health():
    return {"status": "healthy", "mcp_client": mcp_client.__class__.__name__}

@app.get("/api/history")
def get_history():
    """Fetch order history from SQLite."""
    try:
        return get_all_order_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/staples")
def get_staples():
    """Fetch all staples configs from SQLite."""
    try:
        return get_all_staple_configs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/check-triggers")
def check_triggers(
    simulated_date: Optional[str] = Query(None, description="ISO format date, e.g. 2026-07-04T19:30:00"),
    weather: Optional[str] = Query(None, description="Force weather: rainy, hot, pleasant, cold")
):
    """
    Simulates running the scheduled daily job on a specific date and weather condition.
    Triggers both LangGraph engines and returns suggestions.
    """
    try:
        if simulated_date:
            curr_time = datetime.fromisoformat(simulated_date)
        else:
            curr_time = datetime.now()
            
        scheduler = ProactiveDailyScheduler()
        result = scheduler.run_daily_checks(curr_time, weather_override=weather)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/opt-in-staple")
def opt_in_staple(req: StapleOptInRequest):
    """
    Opt-in or opt-out of replenishment tracking for an Instamart item (Hybrid confirmation).
    """
    try:
        is_confirmed = 1 if req.confirm else 0
        config = get_staple_config(req.product_id)
        
        dismiss_cnt = 0
        cycle_len = 4.0
        if config:
            dismiss_cnt = config["dismissed_count"]
            cycle_len = config["cycle_length"] or 4.0

        update_staple_config(
            product_id=req.product_id,
            product_name=req.product_name,
            is_confirmed=is_confirmed,
            dismissed_count=dismiss_cnt,
            cycle_length=cycle_len
        )
        return {"success": True, "message": f"Successfully updated opt-in state for {req.product_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dismiss-pattern")
def dismiss_pattern(req: DismissRequest):
    """
    Dismiss a suggested proactive pattern. If dismissed 3 times, suggestions stop.
    Fulfills trust & safety requirements.
    """
    try:
        today_iso = datetime.now().date().isoformat()
        
        if req.is_staple:
            # Handle staple dismissal in staple_config
            # product_id is the pattern_key here
            config = get_staple_config(req.pattern_key)
            if config:
                new_dismiss_count = config["dismissed_count"] + 1
                update_staple_config(
                    product_id=req.pattern_key,
                    product_name=config["product_name"],
                    is_confirmed=config["is_confirmed"],
                    dismissed_count=new_dismiss_count,
                    cycle_length=config["cycle_length"],
                    last_suggested_date=today_iso
                )
                return {
                    "success": True, 
                    "dismiss_count": new_dismiss_count,
                    "disabled": new_dismiss_count >= 3,
                    "message": f"Dismissed staple. Total dismissals: {new_dismiss_count}/3."
                }
        else:
            # Handle event-based pattern dismissal
            dismissal = get_pattern_dismissal(req.pattern_key)
            new_dismiss_count = 1 if not dismissal else dismissal["dismissed_count"] + 1
            update_pattern_dismissal(req.pattern_key, new_dismiss_count, today_iso)
            return {
                "success": True,
                "dismiss_count": new_dismiss_count,
                "disabled": new_dismiss_count >= 3,
                "message": f"Dismissed pattern. Total dismissals: {new_dismiss_count}/3."
            }
            
        return {"success": False, "message": "Pattern not found."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/order/place")
def place_order(req: OrderRequest):
    """
    Invokes the Swiggy MCP Client to physically place an order (draft becomes active).
    Enforces COD-only and ₹1000 spending caps.
    """
    try:
        if req.order_type == "food":
            if not req.restaurant_id:
                raise HTTPException(status_code=400, detail="restaurant_id is required for food orders.")
            # Map parameters to the BaseSwiggyMCPClient place_food_order tool call
            res = mcp_client.place_food_order(
                restaurant_id=req.restaurant_id,
                items=req.items,
                payment_method=req.payment_method
            )
            return res
        elif req.order_type == "instamart":
            res = mcp_client.checkout_instamart(
                items=req.items,
                payment_method=req.payment_method
            )
            return res
        else:
            raise HTTPException(status_code=400, detail="Invalid order_type. Must be 'food' or 'instamart'.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/order/track/{order_id}")
def track_order(order_id: str, type: str = "food"):
    """
    Live order tracking endpoint.
    Fulfills post-order tracking requirements.
    """
    try:
        if type == "food":
            return mcp_client.track_food_order(order_id)
        else:
            return mcp_client.track_order(order_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
