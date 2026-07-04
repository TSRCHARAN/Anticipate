import random
from typing import List, Dict, Any, Optional
from .base_client import BaseSwiggyMCPClient

class MockSwiggyMCPClient(BaseSwiggyMCPClient):
    """
    Mock Swiggy MCP Client implementation that simulates realistic MCP tool responses.
    This mimics the schema-accurate responses of the real Swiggy Builders Club MCP server.
    
    CRITICAL Swiggy Platform Rules Implemented:
    1. Single-restaurant cart binding: Cart is flushed if you switch restaurants.
    2. Display delivery estimate (deliveryTimeRange) only; no scheduled/future delivery.
    3. Max cart cap of ₹1000 with Cash-On-Delivery (COD) for Builders Club test program.
    4. Simulated live ETA polling that decreases over time for post-order tracking.
    """

    def __init__(self):
        # Local state to simulate server-side session-like caching
        self._current_food_cart_restaurant: Optional[str] = None
        self._current_food_cart_items: List[Dict[str, Any]] = []
        
        # Track simulated orders and their live ETAs (decreases on subsequent calls)
        # Structure: {order_id: {"type": "food"|"instamart", "eta_minutes": int, "status": str}}
        self._active_orders: Dict[str, Dict[str, Any]] = {}

        # Preset database of restaurants and menus
        self._restaurants = [
            {
                "restaurant_id": "rest_001",
                "name": "Meghana Foods",
                "rating": 4.5,
                "distance": 2.1,  # in km
                "deliveryTimeRange": "25-35 MIN",
                "menu": [
                    {"item_id": "m1", "name": "Special Chicken Biryani", "price": 320},
                    {"item_id": "m2", "name": "Paneer Biryani", "price": 280},
                    {"item_id": "m3", "name": "Chicken Boneless Kebab", "price": 240},
                ]
            },
            {
                "restaurant_id": "rest_002",
                "name": "Corner House Ice Creams",
                "rating": 4.7,
                "distance": 1.4,
                "deliveryTimeRange": "15-25 MIN",
                "menu": [
                    {"item_id": "c1", "name": "Death by Chocolate", "price": 290},
                    {"item_id": "c2", "name": "Hot Chocolate Fudge", "price": 220},
                    {"item_id": "c3", "name": "Almond Fudge", "price": 210},
                ]
            },
            {
                "restaurant_id": "rest_003",
                "name": "Truffles",
                "rating": 4.4,
                "distance": 3.8,
                "deliveryTimeRange": "30-45 MIN",
                "menu": [
                    {"item_id": "t1", "name": "All American Cheese Burger", "price": 250},
                    {"item_id": "t2", "name": "Peri Peri Chicken Burger", "price": 270},
                    {"item_id": "t3", "name": "Cold Coffee", "price": 140},
                ]
            },
            {
                "restaurant_id": "rest_004",
                "name": "Empire Restaurant",
                "rating": 4.1,
                "distance": 5.2,  # > 5.0km - Swiggy guardrail warns user!
                "deliveryTimeRange": "40-50 MIN",
                "menu": [
                    {"item_id": "e1", "name": "Ghee Rice", "price": 180},
                    {"item_id": "e2", "name": "Butter Chicken", "price": 290},
                    {"item_id": "e3", "name": "Coin Parotta", "price": 30},
                ]
            }
        ]

        # Preset database of Instamart products
        self._products = [
            {"product_id": "p1", "name": "Nandini Fresh Milk (500ml)", "price": 27, "category": "Dairy & Bread"},
            {"product_id": "p2", "name": "Fresh Eggs (Pack of 6)", "price": 48, "category": "Eggs, Meat & Fish"},
            {"product_id": "p3", "name": "Fresh Bread (White, 400g)", "price": 40, "category": "Dairy & Bread"},
            {"product_id": "p4", "name": "Bananas (Pack of 6)", "price": 35, "category": "Fruits & Vegetables"},
            {"product_id": "p5", "name": "Filtered Water 20L", "price": 90, "category": "Beverages"},
        ]

    def search_restaurants(self, lat: float, lng: float, query: Optional[str] = None) -> List[Dict[str, Any]]:
        # Filter by name query if provided, otherwise return all
        if query:
            q = query.lower()
            return [r for r in self._restaurants if q in r["name"].lower() or any(q in item["name"].lower() for item in r["menu"])]
        return self._restaurants

    def update_food_cart(self, restaurant_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Updates the food cart.
        RULE: Food cart is strictly single-restaurant. Switching restaurants flushes the cart.
        """
        flushed = False
        if self._current_food_cart_restaurant and self._current_food_cart_restaurant != restaurant_id:
            flushed = True
            self._current_food_cart_items = []
            
        self._current_food_cart_restaurant = restaurant_id
        
        # Resolve items with pricing and names
        restaurant = next((r for r in self._restaurants if r["restaurant_id"] == restaurant_id), None)
        if not restaurant:
            raise ValueError(f"Restaurant with ID '{restaurant_id}' not found.")

        resolved_items = []
        cart_total = 0
        for cart_item in items:
            menu_item = next((m for m in restaurant["menu"] if m["item_id"] == cart_item["item_id"]), None)
            if not menu_item:
                raise ValueError(f"Menu item '{cart_item['item_id']}' not found in restaurant '{restaurant_id}'.")
            
            quantity = cart_item["quantity"]
            item_total = menu_item["price"] * quantity
            cart_total += item_total
            resolved_items.append({
                "item_id": menu_item["item_id"],
                "name": menu_item["name"],
                "price": menu_item["price"],
                "quantity": quantity,
                "total": item_total
            })

        self._current_food_cart_items = resolved_items
        
        return {
            "success": True,
            "restaurant_id": restaurant_id,
            "restaurant_name": restaurant["name"],
            "items": resolved_items,
            "total_amount": cart_total,
            "flushed_previous_cart": flushed,
            "delivery_time_estimate": restaurant["deliveryTimeRange"],
            "distance_km": restaurant["distance"]
        }

    def place_food_order(self, restaurant_id: str, items: List[Dict[str, Any]], payment_method: str = "COD") -> Dict[str, Any]:
        """
        Places a food order with COD and ₹1000 limit checks.
        """
        # Form cart to validate total
        cart = self.update_food_cart(restaurant_id, items)
        total = cart["total_amount"]
        
        # Guardrail checks
        if total > 1000:
            return {
                "success": False,
                "error": "CART_CAP_EXCEEDED",
                "message": f"Builders Club test account cap of ₹1000 exceeded. Current cart total: ₹{total}."
            }
        
        if payment_method != "COD":
            return {
                "success": False,
                "error": "COD_ONLY",
                "message": "Builders Club test sandbox is strictly Cash on Delivery (COD)."
            }

        # Generate order
        order_id = f"SWG-FOOD-{random.randint(100000, 999999)}"
        self._active_orders[order_id] = {
            "type": "food",
            "restaurant_name": cart["restaurant_name"],
            "items": cart["items"],
            "total_amount": total,
            "eta_minutes": 35,
            "status": "ORDERED"
        }

        # Clear active cart state
        self._current_food_cart_restaurant = None
        self._current_food_cart_items = []

        return {
            "success": True,
            "order_id": order_id,
            "total_amount": total,
            "status": "ORDER_PLACED",
            "message": "Order placed successfully! Live tracking is now active.",
            "payment_method": "COD"
        }

    def track_food_order(self, order_id: str) -> Dict[str, Any]:
        """
        Tracks a food order and simulates decreasing ETA with sequential polls.
        """
        if order_id not in self._active_orders:
            return {
                "success": False,
                "error": "ORDER_NOT_FOUND",
                "message": f"No active food order found for ID: {order_id}"
            }
        
        order = self._active_orders[order_id]
        
        # Simulate progress
        curr_eta = order["eta_minutes"]
        if curr_eta > 25:
            order["status"] = "PREPARING_FOOD"
            order["eta_minutes"] = max(25, curr_eta - random.randint(2, 5))
        elif curr_eta > 10:
            order["status"] = "RIDER_ASSIGNED"
            order["eta_minutes"] = max(10, curr_eta - random.randint(2, 5))
        elif curr_eta > 2:
            order["status"] = "RIDER_NEARBY"
            order["eta_minutes"] = max(2, curr_eta - random.randint(1, 3))
        else:
            order["status"] = "DELIVERED"
            order["eta_minutes"] = 0

        return {
            "success": True,
            "order_id": order_id,
            "status": order["status"],
            "eta_minutes": order["eta_minutes"],
            "restaurant_name": order["restaurant_name"],
            "items": order["items"],
            "total_amount": order["total_amount"]
        }

    def search_products(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        return [p for p in self._products if q in p["name"].lower() or q in p["category"].lower()]

    def checkout_instamart(self, items: List[Dict[str, Any]], payment_method: str = "COD") -> Dict[str, Any]:
        """
        Simulate checkout of Instamart items.
        Each item is {"product_id": str, "quantity": int}
        """
        resolved_items = []
        total = 0
        for cart_item in items:
            prod = next((p for p in self._products if p["product_id"] == cart_item["product_id"]), None)
            if not prod:
                raise ValueError(f"Product '{cart_item['product_id']}' not found in Instamart.")
            qty = cart_item["quantity"]
            item_total = prod["price"] * qty
            total += item_total
            resolved_items.append({
                "product_id": prod["product_id"],
                "name": prod["name"],
                "price": prod["price"],
                "quantity": qty,
                "total": item_total
            })

        if total > 1000:
            return {
                "success": False,
                "error": "CART_CAP_EXCEEDED",
                "message": f"Builders Club test account cap of ₹1000 exceeded. Instamart total: ₹{total}."
            }

        if payment_method != "COD":
            return {
                "success": False,
                "error": "COD_ONLY",
                "message": "Builders Club test sandbox is strictly Cash on Delivery (COD)."
            }

        order_id = f"SWG-IM-{random.randint(100000, 999999)}"
        self._active_orders[order_id] = {
            "type": "instamart",
            "items": resolved_items,
            "total_amount": total,
            "eta_minutes": 20,
            "status": "ORDERED"
        }

        return {
            "success": True,
            "order_id": order_id,
            "total_amount": total,
            "status": "ORDER_PLACED",
            "message": "Instamart order placed successfully!",
            "payment_method": "COD"
        }

    def track_order(self, order_id: str) -> Dict[str, Any]:
        """
        Track Instamart order. Same live-poll simulation.
        """
        if order_id not in self._active_orders:
            return {
                "success": False,
                "error": "ORDER_NOT_FOUND",
                "message": f"No active Instamart order found for ID: {order_id}"
            }
        
        order = self._active_orders[order_id]
        curr_eta = order["eta_minutes"]
        
        # Simulate progress
        if curr_eta > 15:
            order["status"] = "PACKING_STAPLES"
            order["eta_minutes"] = max(15, curr_eta - random.randint(2, 4))
        elif curr_eta > 8:
            order["status"] = "RIDER_DISPATCHED"
            order["eta_minutes"] = max(8, curr_eta - random.randint(2, 4))
        elif curr_eta > 2:
            order["status"] = "RIDER_ARRIVING_SOON"
            order["eta_minutes"] = max(2, curr_eta - random.randint(1, 3))
        else:
            order["status"] = "DELIVERED"
            order["eta_minutes"] = 0

        return {
            "success": True,
            "order_id": order_id,
            "status": order["status"],
            "eta_minutes": order["eta_minutes"],
            "items": order["items"],
            "total_amount": order["total_amount"]
        }
