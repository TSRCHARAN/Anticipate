import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# Append src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.db.db import get_all_order_history
from src.weather.weather_client import WeatherClient
from src.agents.event_trigger import run_event_trigger
from src.agents.consumption_trigger import run_consumption_trigger

class ProactiveDailyScheduler:
    """
    Simulates the APScheduler daily cron runner that triggers the agent predictive models.
    Coordinates trigger evaluation, handles weather classification, and applies merge logic.
    """

    def __init__(self, lat: float = 12.9716, lng: float = 77.5946):
        self.lat = lat
        self.lng = lng
        self.weather_client = WeatherClient()

    def run_daily_checks(self, current_time: datetime, weather_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs both event-based and consumption-based triggers.
        Returns suggestions, applying merge logic if both triggers fire.
        """
        print(f"[SCHEDULER] Running daily proactive agent checks for date: {current_time.date()}...")

        # 1. Fetch weather bucket
        weather_bucket = self.weather_client.get_weather_bucket(self.lat, self.lng, mock_override=weather_override)
        print(f"[SCHEDULER] Weather bucket evaluated: {weather_bucket}")

        # 2. Pull order history from database
        history = get_all_order_history()

        # 3. Execute Event-Based Trigger Model (LangGraph)
        event_suggestions = run_event_trigger(
            current_time=current_time,
            weather=weather_bucket,
            lat=self.lat,
            lng=self.lng,
            order_history=history
        )

        # 4. Execute Consumption-Based Trigger Model (LangGraph)
        consumption_res = run_consumption_trigger(
            current_time=current_time,
            order_history=history
        )
        consumption_suggestions = consumption_res.get("suggestions", [])
        candidate_staples = consumption_res.get("candidate_staples", [])

        # 5. MERGE LOGIC: Prevent notification spamming
        suggestions = []
        if event_suggestions and consumption_suggestions:
            print("[SCHEDULER] Both Event and Consumption triggers fired on the same day. Merging suggestions.")
            # Merge into a single Daily Digest Suggestion
            merged_items = []
            explanations = []
            
            # Since Swiggy requires separate checkout pathways physically (grocery vs restaurant), 
            # we bundle them conceptually in a single notification response card.
            merged_suggestion = {
                "trigger_type": "merged",
                "order_type": "mixed",
                "explanation": "Here is your Proactive Daily Digest! We combined your evening food pattern and groceries into a single notification to avoid spamming you.",
                "sub_suggestions": event_suggestions + consumption_suggestions,
                "pattern_key": "merged_daily_digest"
            }
            suggestions.append(merged_suggestion)
        else:
            # Just add whatever fired
            suggestions.extend(event_suggestions)
            suggestions.extend(consumption_suggestions)

        return {
            "date": current_time.date().isoformat(),
            "weather": weather_bucket,
            "suggestions": suggestions,
            "candidate_staples": candidate_staples
        }
