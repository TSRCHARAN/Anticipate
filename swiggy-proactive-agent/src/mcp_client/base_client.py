from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseSwiggyMCPClient(ABC):
    """
    Abstract interface for Swiggy MCP Client.
    Exposes high-level methods that map directly to Swiggy Builders Club MCP Tools.
    This contract ensures that swapping the mock implementation for a production
    MCP server client requires zero changes in the agent orchestration layer.
    """

    @abstractmethod
    def search_restaurants(self, lat: float, lng: float, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for food restaurants near coordinates.
        Maps to the 'search_restaurants' MCP tool.
        Returns fields: name, rating, distance, deliveryTimeRange, restaurant_id, menu
        """
        pass

    @abstractmethod
    def update_food_cart(self, restaurant_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update items in the food cart.
        Maps to the 'update_food_cart' MCP tool.
        Note: The cart is strictly bound to a single restaurant.
        Updating with a different restaurant_id flushes the previous cart.
        Each item is of the form {"item_id": str, "quantity": int}.
        """
        pass

    @abstractmethod
    def place_food_order(self, restaurant_id: str, items: List[Dict[str, Any]], payment_method: str = "COD") -> Dict[str, Any]:
        """
        Place a food order using Cash on Delivery (COD is mandated by Builders Club, ₹1000 limit).
        Maps to 'place_food_order' MCP tool.
        """
        pass

    @abstractmethod
    def track_food_order(self, order_id: str) -> Dict[str, Any]:
        """
        Track live food order status and active ETA.
        Maps to the 'track_food_order' MCP tool.
        """
        pass

    @abstractmethod
    def search_products(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Instamart products.
        Maps to 'search_products' MCP tool.
        """
        pass

    @abstractmethod
    def checkout_instamart(self, items: List[Dict[str, Any]], payment_method: str = "COD") -> Dict[str, Any]:
        """
        Checkout and place an Instamart staple order.
        Maps to 'checkout' MCP tool.
        """
        pass

    @abstractmethod
    def track_order(self, order_id: str) -> Dict[str, Any]:
        """
        Track active Instamart order.
        Maps to 'track_order' MCP tool.
        """
        pass
