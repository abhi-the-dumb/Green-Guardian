import requests  # For making HTTP requests

from django.http import JsonResponse  # For forecast response
from rest_framework.decorators import api_view  # For DRF API views
from rest_framework.response import Response  # For DRF responses
from rest_framework import status  # For HTTP status codes


@api_view(['GET'])
def historical_weather(request, lat, lon, start, end):
    """
    Fetch historical weather data from Open-Meteo API
    """
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start}&end_date={end}"
        f"&hourly=temperature_2m,relative_humidity_2m,soil_moisture_0_to_7cm"
        f"&timezone=auto"
    )

    try:
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200 or "error" in data:
            return Response({"error": data.get("reason", "Failed to fetch historical weather")},
                            status=response.status_code)

        # ✅ Use correct keys: "latitude", "longitude"
        historical_data = {
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "timezone": data.get("timezone"),
            "hourly": data.get("hourly", {})
        }

        return Response(historical_data)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def forecast(request, lat, lon):
    try:
        # Build forecast URL
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=precipitation_sum,temperature_2m_max,temperature_2m_min"
            f"&hourly=relativehumidity_2m"
            f"&forecast_days=1&timezone=auto"
        )
        forecast_resp = requests.get(forecast_url, timeout=10)
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()

        # Extract daily values
        daily = forecast_data.get("daily", {})
        hourly = forecast_data.get("hourly", {})

        # Convert hourly humidity into daily min/max
        humidity_by_day = {}
        if "time" in hourly and "relativehumidity_2m" in hourly:
            for t, h in zip(hourly["time"], hourly["relativehumidity_2m"]):
                date = t.split("T")[0]  # cut off hour
                humidity_by_day.setdefault(date, []).append(h)

        humidity_min, humidity_max = [], []
        for d in daily.get("time", []):
            values = humidity_by_day.get(d, [])
            if values:
                humidity_min.append(min(values))
                humidity_max.append(max(values))
            else:
                humidity_min.append(None)
                humidity_max.append(None)

        # Return only precipitation + humidity
        return JsonResponse({
            "success": True,
            "data": {
                "dates": daily.get("time", []),
                "rainfall_mm": daily.get("precipitation_sum", []),
                "humidity_min": humidity_min,
                "humidity_max": humidity_max,
            }
        })

    except requests.exceptions.RequestException as e:
        return JsonResponse({"success": False, "error": str(e)}, status=502)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
@api_view(['GET'])
def geocoding(request, city):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"

    try:
        response = requests.get(url)
        data = response.json()
        
        if response.status_code != 200 or not data:
            return Response({"error": "Failed to fetch geocoding data"}, status=response.status_code)
        
        # Return the first result
        result = data["results"]
        return Response(result)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def weather_info(request, city):
    try:
        # Step 1: Get coordinates
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
        geo_resp = requests.get(geo_url, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        
        if not geo_data.get("results"):
            return JsonResponse({"success": False, "error": "City not found"}, status=404)
        
        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]
        
        # Step 2: Get forecast (rainfall + humidity)
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=precipitation_sum,relativehumidity_2m_max,relativehumidity_2m_min"
            f"&forecast_days=7&timezone=auto"
        )
        forecast_resp = requests.get(forecast_url, timeout=10)
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()
        
        # Return only daily humidity and rainfall
        daily = forecast_data.get("daily", {})
        return JsonResponse({
            "success": True,
            "data": {
                "dates": daily.get("time", []),
                "rainfall_mm": daily.get("precipitation_sum", []),
                "humidity_max": daily.get("relativehumidity_2m_max", []),
                "humidity_min": daily.get("relativehumidity_2m_min", [])
            }
        })
    
    except requests.exceptions.RequestException as e:
        return JsonResponse({"success": False, "error": str(e)}, status=502)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
