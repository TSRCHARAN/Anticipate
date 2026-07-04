from pydantic import BaseModel, Field
from typing import Optional, List

class OrderHistoryRecord(BaseModel):
    id: Optional[int] = None
    order_type: str  # 'food' or 'instamart'
    restaurant_id: Optional[str] = None
    restaurant_name: Optional[str] = None
    item_id: str
    item_name: str
    price: float
    quantity: int
    order_time: str  # ISO string
    day_of_week: int  # 0 to 6
    hour: int  # 0 to 23
    weather_condition: str  # 'rainy', 'hot', 'pleasant', 'cold'

class StapleConfigRecord(BaseModel):
    product_id: str
    product_name: str
    is_confirmed: bool = False
    dismissed_count: int = 0
    last_suggested_date: Optional[str] = None
    cycle_length: Optional[float] = None

class PatternDismissalRecord(BaseModel):
    pattern_key: str
    dismissed_count: int = 0
    last_dismissed_date: Optional[str] = None

class DraftSuggestion(BaseModel):
    trigger_type: str  # 'event_based' | 'consumption_based' | 'merged'
    order_type: str  # 'food' | 'instamart'
    restaurant_id: Optional[str] = None
    restaurant_name: Optional[str] = None
    product_id: Optional[str] = None  # for instamart staples
    items: List[dict]  # List of {"item_id"/"product_id": str, "name": str, "quantity": int, "price": float}
    total_amount: float
    explanation: str
    pattern_key: str  # key to track dismissals
