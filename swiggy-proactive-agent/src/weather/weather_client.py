import os
import requests
from typing import Optional

class WeatherClient:
    """
    Interfaces with OpenWeatherMap or falls back to simulated weather.
    Buckets weather conditions into four simple categories: rainy, hot, pleasant, cold.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")

    def get_weather_bucket(self, lat: float, lng: float, mock_override: Optional[str] = None) -> str:
        """
        Gets the weather bucket for coordinates.
        Allows a mock_override string ('rainy', 'hot', 'pleasant', 'cold') for testing or demo purposes.
        """
        if mock_override:
            return mock_override

        if not self.api_key:
            # Safe default for the Builders Club sandbox demo
            return "rainy"

        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={self.api_key}&units=metric"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                temp = data["main"]["temp"]
                weather_main = data["weather"][0]["main"].lower()

                # Classification Logic
                if "rain" in weather_main or "drizzle" in weather_main or "thunderstorm" in weather_main:
                    return "rainy"
                elif temp >= 32:
                    return "hot"
                elif temp <= 16:
                    return "cold"
                else:
                    return "pleasant"
        except Exception as e:
            print(f"[WEATHER] Error fetching real weather: {e}. Falling back to default 'rainy'.")
        
        return "rainy"
