from typing import Optional

class WeatherClient:
    """
    A simulated weather client that classifies the weather into buckets
    (rainy, hot, pleasant, cold) for pattern matching calculations in the 
    proactive ordering system.
    """

    def __init__(self):
        pass

    def get_weather_bucket(self, lat: float, lng: float, mock_override: Optional[str] = None) -> str:
        """
        Classifies weather conditions at the coordinates.
        Supports overrides for precise sandbox simulation testing.
        """
        if mock_override:
            # Enforce lowercase and validate
            override_val = mock_override.lower()
            if override_val in ["rainy", "pleasant", "hot", "cold"]:
                return override_val
        
        # Default fallback bucket
        return "rainy"
