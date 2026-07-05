import random
from typing import List, Dict, Any, Optional

class MockSwiggyMCPClient:
    """
    A simulated Swiggy MCP Client that models physical order dispatch, checkout rules,
    and post-order tracking tickers in the Builders Club sandbox environment.
    """

    def __init__(self):
        # Cache of placed orders so they can be tracked realistically
        self._placed_orders: Dict[str, Dict[str, Any]] = {}

    def place_food_order(self, restaurant_id: str, items: List[Dict[str, Any]], payment_method: str = "COD") -> Dict[str, Any]:
        """
        Mocks checkout of a food order, enforcing COD-only and ₹1000 spending cap.
        """
        # 1. Enforce COD-only guardrail
        if payment_method != "COD":
            return {
                "success": False,
                "error": "Builders Club Safety Mandate: Checkout must be Cash on Delivery (COD) in sandbox mode."
            }

        # 2. Enforce ₹1000 spending cap
        total_amount = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
        if total_amount > 1000:
            return {
                "success": False,
                "error": f"Builders Club Safety Mandate: Carts are strictly capped at ₹1000. Your total was ₹{total_amount}."
            }

        order_id = f"SWG-FOOD-{random.randint(100000, 999999)}"
        order_details = {
            "order_id": order_id,
            "type": "food",
            "restaurant_id": restaurant_id,
            "items": items,
            "total_amount": total_amount,
            "payment_method": payment_method,
            "status": "ORDERED",
            "eta_minutes": 35,
            "created_time": random.randint(1, 100) # dummy sequence
        }
        self._placed_orders[order_id] = order_details

        return {
            "success": True,
            "order_id": order_id,
            "status": "ORDERED",
            "total_amount": total_amount,
            "eta_minutes": 35,
            "message": "Food order successfully registered in MCP Sandbox."
        }

    def checkout_instamart(self, items: List[Dict[str, Any]], payment_method: str = "COD") -> Dict[str, Any]:
        """
        Mocks checkout of an Instamart grocery order, enforcing COD-only and ₹1000 spending cap.
        """
        # 1. Enforce COD-only guardrail
        if payment_method != "COD":
            return {
                "success": False,
                "error": "Builders Club Safety Mandate: Checkout must be Cash on Delivery (COD) in sandbox mode."
            }

        # 2. Enforce ₹1000 spending cap
        total_amount = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
        if total_amount > 1000:
            return {
                "success": False,
                "error": f"Builders Club Safety Mandate: Carts are strictly capped at ₹1000. Your total was ₹{total_amount}."
            }

        order_id = f"SWG-IM-{random.randint(100000, 999999)}"
        order_details = {
            "order_id": order_id,
            "type": "instamart",
            "items": items,
            "total_amount": total_amount,
            "payment_method": payment_method,
            "status": "ORDERED",
            "eta_minutes": 20,
            "created_time": random.randint(1, 100)
        }
        self._placed_orders[order_id] = order_details

        return {
            "success": True,
            "order_id": order_id,
            "status": "ORDERED",
            "total_amount": total_amount,
            "eta_minutes": 20,
            "message": "Instamart grocery order successfully registered in MCP Sandbox."
        }

    def track_food_order(self, order_id: str) -> Dict[str, Any]:
        """
        Polled post-order tracking ticker for food orders.
        """
        return self._track_general_order(order_id, default_type="food")

    def track_order(self, order_id: str) -> Dict[str, Any]:
        """
        Polled post-order tracking ticker for Instamart grocery orders.
        """
        return self._track_general_order(order_id, default_type="instamart")

    def _track_general_order(self, order_id: str, default_type: str) -> Dict[str, Any]:
        if order_id not in self._placed_orders:
            # Generate a mock state if not found to remain robust in UI
            is_food = "FOOD" in order_id
            return {
                "order_id": order_id,
                "status": "PREPARING" if is_food else "PACKING",
                "eta_minutes": 25 if is_food else 15,
                "details": f"Mocked status update for order {order_id}"
            }

        order = self._placed_orders[order_id]
        
        # Advance status simple state machine for demo realism
        current_status = order["status"]
        eta = order["eta_minutes"]

        if current_status == "ORDERED":
            next_status = "PREPARING" if order["type"] == "food" else "PACKING"
            next_eta = max(0, eta - 5)
        elif current_status in ["PREPARING", "PACKING"]:
            next_status = "DISPATCHED"
            next_eta = max(0, eta - 10)
        elif current_status == "DISPATCHED":
            next_status = "RIDER_NEARBY"
            next_eta = max(0, eta - 5)
        elif current_status == "RIDER_NEARBY":
            next_status = "DELIVERED"
            next_eta = 0
        else:
            next_status = "DELIVERED"
            next_eta = 0

        order["status"] = next_status
        order["eta_minutes"] = next_eta

        return {
            "order_id": order_id,
            "status": next_status,
            "eta_minutes": next_eta,
            "total_amount": order["total_amount"],
            "items_count": len(order["items"])
        }
