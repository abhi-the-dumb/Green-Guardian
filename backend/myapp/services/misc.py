import os
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response  # fixed import
from rest_framework import status              # fixed import
import requests
from dotenv import load_dotenv
import re

# Load environment variables from .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

MEERSENS_URL = os.getenv("MEERSENS_URL")
MEERSENS_API_KEY = os.getenv("MEERSENS_API_KEY")
API_URL = os.getenv("CROP_PRICE_API_URL", "API_KEY_DATA_URL")    
API_PARAMS = {
    "api-key": os.getenv("CROP_PRICE_API_KEY", "API_KEY_DATA"),
    "format": "json",
    "limit": 1000
}

def sanitize_input(text, max_length=255):
    """Sanitize string input for safety."""
    if not isinstance(text, str):
        return ""
    # Remove potentially dangerous characters
    cleaned = re.sub(r'[<>"\']', '', text.strip())
    return cleaned[:max_length]

def load_data():
    try:
        response = requests.get(API_URL, params=API_PARAMS, timeout=10)
        response.raise_for_status()
        return response.json().get("records", [])
    except requests.RequestException as e:
        print(f"API request failed: {str(e)}")
        return []

# Load the data once at module import
DATA = load_data()

@api_view(['GET'])
def water_data(request, lat, lon):
    url = f"{MEERSENS_URL}/water/current"
    headers = {"apikey": MEERSENS_API_KEY}
    params = {
        "lat": lat,
        "lng": lon,
        "index_type": "meersens",
        "health_recommendations": "true"
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if not data.get("found", True):
            return JsonResponse({"message": "No water data available for this location."}, status=404)

        return JsonResponse(data, safe=False, status=r.status_code)

    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": str(e)}, status=502)

@api_view(['GET'])
def aqi_info(request, lat, lon):
    """
    Fetch AQI info from OpenWeather API for given latitude and longitude
    """
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OPEN_WEATHER_API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            return Response({"error": data.get("message", "Failed to fetch AQI")}, status=response.status_code)

        # Air Pollution API returns something like:
        # { "coord": {...}, "list": [ { "main": {"aqi": 1}, "components": {...}, "dt": 1693872000 } ] }
        forecast_list = []
        for entry in data.get('list', []):
            forecast_list.append({
                "aqi": entry['main']['aqi'],               # 1 = Good, 5 = Very Poor
                "components": entry['components'],        # CO, NO2, PM2.5, etc.
                "timestamp": entry['dt']
            })
        
        return Response(data)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_states(request):
    crop = sanitize_input(request.GET.get('crop', ''), 100).lower()
    if not crop:
        return Response([])
    states = sorted({r['state'] for r in DATA if r.get('commodity', '').lower() == crop})
    return Response(states)
