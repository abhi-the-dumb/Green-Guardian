from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
# from ml_model.crop_recommendation import predict_crop
# from ml_model.crop_yield_predictor import predict_yield
# from ml_model.fertiser_recommendation import predict_fertilizer
from django.core.cache import cache
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
import json
import joblib
import pandas as pd
import os
from dotenv import load_dotenv
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
import requests

OPEN_WEATHER_API_KEY = 'b021468e664ba9173a7d281681b058e1'

GROQ_API_KEY = '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'

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"

CEDA_API_KEY = '8e5023a508018684471dc42dd81677e0f7dcae16c765e1c967bad1da7d599739'  #valid till Fri Sep 12 2025 03:54:46

CEDA_URL = 'https://api.ceda.ashoka.edu.in/api/v1/agmarknet/'

# Valid till 15 days from now probably end on 20 Sep 2025
MEERSENS_API_KEY = 'NF9SJdvxLdqycxdvkLMAhIqggCIFldwr' #site https://eaas.meersens.com/api/me

MEERSENS_URL = 'https://api.meersens.com/environment/public'


SOILGRIDS_PROPERTIES_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
SOILGRIDS_CLASSIFICATION_URL = "https://rest.isric.org/soilgrids/v2.0/classification/query"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


# Global API config
API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
API_PARAMS = {
    "api-key": "579b464db66ec23bdd000001c43ef34767ce496343897dfb1893102b",
    "format": "json",
    "limit": 1000
}

import re

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

def sanitize_input(text, max_length=255):
    """Sanitize string input for safety."""
    if not isinstance(text, str):
        return ""
    # Remove potentially dangerous characters
    cleaned = re.sub(r'[<>"\']', '', text.strip())
    return cleaned[:max_length]

def get_coordinates_from_pincode(pincode: str):
    params = {
        "postalcode": pincode,
        "country": "India",
        "format": "json"
    }
    headers = {"User-Agent": "soil-api/1.0"}
    resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=30)
    data = resp.json()
    if not data:
        return None, None
    return float(data[0]["lat"]), float(data[0]["lon"])


# def fetch_soilgrids(lat: float, lon: float):
#     params = {
#         "lat": lat,
#         "lon": lon,
#         "property": [
#             "bdod", "cec", "cfvo", "clay", "nitrogen", "ocd", "ocs",
#             "phh2o", "sand", "silt", "soc", "wv0010", "wv0033", "wv1500"
#         ],
#         "depth": [
#             "0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm",
#             "100-200cm", "0-30cm"
#         ],
#         "value": ["Q0.5", "Q0.05", "Q0.95", "mean", "uncertainty"]
#     }

#     cache_key = f"soil_{lat}_{lon}"
#     cached = cache.get(cache_key)
#     if cached:
#         return cached

#     try:
#         resp = requests.get(SOILGRIDS_PROPERTIES_URL, params=params, timeout=20)
#         resp.raise_for_status()   # raises error on bad status
#         data = resp.json()
#         cache.set(cache_key, data, timeout=60*60*24)  # cache for 1 day
#         return data
#     except requests.exceptions.Timeout:
#         # fallback if API is too slow
#         return {}
#     except Exception as e:
#         return {"error": str(e)}

# @csrf_exempt
# def get_soilgrids(request, lat, lon):
#     try:
#         lat = float(lat)
#         lon = float(lon)
#         resp = requests.get(SOILGRIDS_PROPERTIES_URL, params={
#             "lat": lat,
#             "lon": lon,
#             "property": [
#                 "bdod","cec","cfvo","clay","nitrogen","ocd","ocs",
#                 "phh2o","sand","silt","soc","wv0010","wv0033","wv1500"
#             ],
#             "depth":["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm","0-30cm"],
#             "value":["Q0.5","Q0.05","Q0.95","mean","uncertainty"]
#         }, timeout=60)
#         raw_data = resp.json()
#         return JsonResponse(raw_data, safe=False)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)


# # Helper: Fetch soil classification
# def fetch_soil_classification(lat: float, lon: float):
#     params = {"lat": lat, "lon": lon, "number_classes": 5}
#     resp = requests.get(SOILGRIDS_CLASSIFICATION_URL, params=params, timeout=30)
#     return resp.json()


# @csrf_exempt
# def fetch_soil_classification_view(request, lat, lon):
#     try:
#         lat = float(lat)
#         lon = float(lon)
#         data = fetch_soil_classification(lat, lon)
#         return JsonResponse(data, safe=False)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)


# @csrf_exempt
# def get_soilgrids(request, lat, lon):
#     try:
#         lat = float(lat)
#         lon = float(lon)
#         raw_data = fetch_soilgrids(lat, lon)

#         properties = raw_data.get("properties", {})
#         def extract_single_value(prop_name, depth_label="0-5cm", stat="mean"):
#             layers = properties.get("layers", [])
#             for layer in layers:
#                 if layer.get("name") == prop_name:
#                     for d in layer.get("depths", []):
#                         if d.get("label") == depth_label:
#                             return d.get("values", {}).get(stat)
#             return None



#         filtered = {
#             "nitrogen": extract_single_value("nitrogen"),
#             "soil_moisture": {
#                 "wv0033": extract_single_value("wv0033"),
#                 "wv1500": extract_single_value("wv1500"),
#             },
#             "ph": extract_single_value("phh2o"),
#         }

#         classification = fetch_soil_classification(lat, lon)
#         filtered["soil_type"] = classification.get("wrb_class_name")

#         return JsonResponse(filtered, safe=False)

#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)

# def extract(props, soil_data, depth="0-5cm", stat="mean"):
#     if isinstance(props, str):
#         props = [props]
#     for layer in soil_data.get("properties", {}).get("layers", []):
#         for prop in props:
#             if prop in layer.get("name", "").lower():
#                 for d in layer.get("depths", []):
#                     if depth in d.get("label", ""):
#                         values = d.get("values", {})
#                         return values.get(stat) or list(values.values())[0]
#     return None

# @csrf_exempt
# # def auto_crop_recommendation(request, lat, lon):
# #     '''
# #     $ curl http://127.0.0.1:8000/api/auto-crop-recommendation/15.3/75.2/            

# # {"success": true, "inputs": {"N": 50, "P": 20, "K": 30, "temperature": 24.75, "humidity": 85.79166666666667, "ph": 6.5, "rainfall": 1.6}, "prediction": "muskmelon"}% 
# # '''
# #     try:
# #         lat = float(lat)
#         lon = float(lon)

#         # 1. Get Soil Data
#         soil_raw = fetch_soilgrids(lat, lon)
#         nitrogen = extract(["nitrogen", "nitrogen_tot"], soil_raw) or 50
#         ph = extract(["phh2o", "ph"], soil_raw) or 6.5

#         if nitrogen is None or ph is None:
#             return JsonResponse({"error": "Insufficient soil data"}, status=500)

#         # 2. Get Weather Data (Open-Meteo)
#         forecast_url = (
#             f"https://api.open-meteo.com/v1/forecast?"
#             f"latitude={lat}&longitude={lon}"
#             f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
#             f"&hourly=relativehumidity_2m"
#             f"&forecast_days=1&timezone=auto"
#         )
#         weather_resp = requests.get(forecast_url, timeout=10).json()

#         daily = weather_resp.get("daily", {})
#         hourly = weather_resp.get("hourly", {})

#         # Temperature
#         temperature = None
#         if "temperature_2m_max" in daily and "temperature_2m_min" in daily:
#             temperature = (daily["temperature_2m_max"][0] + daily["temperature_2m_min"][0]) / 2

#         # Rainfall
#         rainfall = daily.get("precipitation_sum", [None])[0]

#         # Humidity (average of today’s hourly values)
#         humidity = None
#         if "time" in hourly and "relativehumidity_2m" in hourly and daily.get("time"):
#             today = daily["time"][0]
#             values = [h for t, h in zip(hourly["time"], hourly["relativehumidity_2m"]) if t.startswith(today)]
#             if values:
#                 humidity = sum(values) / len(values)

#         if None in [temperature, humidity, rainfall]:
#             return JsonResponse({"error": "Weather data missing"}, status=500)

#         # 3. Run ML Crop Recommendation
#         P = 20  # TODO: replace with real phosphorus
#         K = 30  # TODO: replace with real potassium

#         crop = predict_crop(nitrogen, P, K, temperature, humidity, ph, rainfall)

#         return JsonResponse({
#             "success": True,
#             "inputs": {
#                 "N": nitrogen, "P": P, "K": K,
#                 "temperature": temperature,
#                 "humidity": humidity,
#                 "ph": ph,
#                 "rainfall": rainfall
#             },
#             "prediction": crop
#         })

#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)


# @csrf_exempt
# def auto_fertilizer_recommendation(request, lat, lon, crop_type):
#     '''
#     $ curl http://127.0.0.1:8000/api/auto-fertilizer-recommendation/15.3/75.2/Maize/

# {"success": true, "inputs": {"crop": "Maize", "N": 153, "P": 20, "K": 30, "temperature": 24.75, "humidity": 85.79166666666667, "rainfall": 1.6}, "recommendation": "Urea"}%   
# '''
#     try:
#         lat = float(lat)
#         lon = float(lon)

#         # 1. Get Soil Data
#         soil_raw = fetch_soilgrids(lat, lon)
#         N = extract(["nitrogen", "nitrogen_tot"], soil_raw)
#         P = extract(["phosphorus", "phosphorus_tot"], soil_raw) or 20
#         K = extract(["potassium", "potassium_tot"], soil_raw) or 30
#         ph = extract(["phh2o", "ph"], soil_raw)

#         if N is None or ph is None:
#             return JsonResponse({"error": "Insufficient soil data"}, status=500)

#         # 2. Get Weather Data (Open-Meteo)
#         forecast_url = (
#             f"https://api.open-meteo.com/v1/forecast?"
#             f"latitude={lat}&longitude={lon}"
#             f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
#             f"&hourly=relativehumidity_2m"
#             f"&forecast_days=1&timezone=auto"
#         )
#         weather_resp = requests.get(forecast_url, timeout=10).json()

#         daily = weather_resp.get("daily", {})
#         hourly = weather_resp.get("hourly", {})

#         # Temperature
#         temperature = None
#         if "temperature_2m_max" in daily and "temperature_2m_min" in daily:
#             temperature = (daily["temperature_2m_max"][0] + daily["temperature_2m_min"][0]) / 2

#         # Rainfall
#         rainfall = daily.get("precipitation_sum", [None])[0]

#         # Humidity
#         humidity = None
#         if "time" in hourly and "relativehumidity_2m" in hourly and daily.get("time"):
#             today = daily["time"][0]
#             values = [h for t, h in zip(hourly["time"], hourly["relativehumidity_2m"]) if t.startswith(today)]
#             if values:
#                 humidity = sum(values) / len(values)

#         if None in [temperature, humidity, rainfall]:
#             return JsonResponse({"error": "Weather data missing"}, status=500)

#         # 3. Call Fertilizer Model (or Rule-Based System)
#         recommendation = predict_fertilizer(
#             temperature=temperature,
#             humidity=humidity,
#             # ph=ph,
#             moisture = 20,
#             soil_type="Loamy",   # TODO: replace with soil classification if available
#             crop_type=crop_type,
#             nitrogen=N,
#             phosphorous=P,
#             potassium=K,
#             # rainfall=rainfall
#         )

#         return JsonResponse({
#             "success": True,
#             "inputs": {
#                 "crop": crop_type,
#                 "N": N, "P": P, "K": K,
#                 "temperature": temperature,
#                 "humidity": humidity,
#                 # "ph": ph,
#                 "rainfall": rainfall
#             },
#             "recommendation": recommendation
#         })

#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)


# @api_view(['GET'])
# def geocoding(request, city):
#     url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"

#     try:
#         response = requests.get(url)
#         data = response.json()
        
#         if response.status_code != 200 or not data:
#             return Response({"error": "Failed to fetch geocoding data"}, status=response.status_code)
        
#         # Return the first result
#         result = data["results"]
#         return Response(result)
    
#     except Exception as e:
#         return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# def weather_info(request, city):
#     try:
#         # Step 1: Get coordinates
#         geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
#         geo_resp = requests.get(geo_url, timeout=10)
#         geo_resp.raise_for_status()
#         geo_data = geo_resp.json()
        
#         if not geo_data.get("results"):
#             return JsonResponse({"success": False, "error": "City not found"}, status=404)
        
#         lat = geo_data["results"][0]["latitude"]
#         lon = geo_data["results"][0]["longitude"]
        
#         # Step 2: Get forecast (rainfall + humidity)
#         forecast_url = (
#             f"https://api.open-meteo.com/v1/forecast?"
#             f"latitude={lat}&longitude={lon}"
#             f"&daily=precipitation_sum,relativehumidity_2m_max,relativehumidity_2m_min"
#             f"&forecast_days=7&timezone=auto"
#         )
#         forecast_resp = requests.get(forecast_url, timeout=10)
#         forecast_resp.raise_for_status()
#         forecast_data = forecast_resp.json()
        
#         # Return only daily humidity and rainfall
#         daily = forecast_data.get("daily", {})
#         return JsonResponse({
#             "success": True,
#             "data": {
#                 "dates": daily.get("time", []),
#                 "rainfall_mm": daily.get("precipitation_sum", []),
#                 "humidity_max": daily.get("relativehumidity_2m_max", []),
#                 "humidity_min": daily.get("relativehumidity_2m_min", [])
#             }
#         })
    
#     except requests.exceptions.RequestException as e:
#         return JsonResponse({"success": False, "error": str(e)}, status=502)
#     except Exception as e:
#         return JsonResponse({"success": False, "error": str(e)}, status=500)

# @api_view(['GET'])
# def aqi_info(request, lat, lon):
#     """
#     Fetch AQI info from OpenWeather API for given latitude and longitude
#     """
#     url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OPEN_WEATHER_API_KEY}"
    
#     try:
#         response = requests.get(url)
#         data = response.json()

#         if response.status_code != 200:
#             return Response({"error": data.get("message", "Failed to fetch AQI")}, status=response.status_code)

#         # Air Pollution API returns something like:
#         # { "coord": {...}, "list": [ { "main": {"aqi": 1}, "components": {...}, "dt": 1693872000 } ] }
#         forecast_list = []
#         for entry in data.get('list', []):
#             forecast_list.append({
#                 "aqi": entry['main']['aqi'],               # 1 = Good, 5 = Very Poor
#                 "components": entry['components'],        # CO, NO2, PM2.5, etc.
#                 "timestamp": entry['dt']
#             })
        
#         return Response(data)

#     except Exception as e:
#         return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# # @api_view(['GET'])
# def historical_weather(request, lat, lon, start, end):
#     """
#     Fetch historical weather data from Open-Meteo API
#     """
#     url = (
#         f"https://archive-api.open-meteo.com/v1/archive"
#         f"?latitude={lat}&longitude={lon}"
#         f"&start_date={start}&end_date={end}"
#         f"&hourly=temperature_2m,relative_humidity_2m,soil_moisture_0_to_7cm"
#         f"&timezone=auto"
#     )

#     try:
#         response = requests.get(url)
#         data = response.json()

#         if response.status_code != 200 or "error" in data:
#             return Response({"error": data.get("reason", "Failed to fetch historical weather")},
#                             status=response.status_code)

#         # ✅ Use correct keys: "latitude", "longitude"
#         historical_data = {
#             "latitude": data.get("latitude"),
#             "longitude": data.get("longitude"),
#             "timezone": data.get("timezone"),
#             "hourly": data.get("hourly", {})
#         }

#         return Response(historical_data)

#     except Exception as e:
#         return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# def forecast(request, lat, lon):
#     try:
#         # Build forecast URL
#         forecast_url = (
#             f"https://api.open-meteo.com/v1/forecast?"
#             f"latitude={lat}&longitude={lon}"
#             f"&daily=precipitation_sum,temperature_2m_max,temperature_2m_min"
#             f"&hourly=relativehumidity_2m"
#             f"&forecast_days=1&timezone=auto"
#         )
#         forecast_resp = requests.get(forecast_url, timeout=10)
#         forecast_resp.raise_for_status()
#         forecast_data = forecast_resp.json()

#         # Extract daily values
#         daily = forecast_data.get("daily", {})
#         hourly = forecast_data.get("hourly", {})

#         # Convert hourly humidity into daily min/max
#         humidity_by_day = {}
#         if "time" in hourly and "relativehumidity_2m" in hourly:
#             for t, h in zip(hourly["time"], hourly["relativehumidity_2m"]):
#                 date = t.split("T")[0]  # cut off hour
#                 humidity_by_day.setdefault(date, []).append(h)

#         humidity_min, humidity_max = [], []
#         for d in daily.get("time", []):
#             values = humidity_by_day.get(d, [])
#             if values:
#                 humidity_min.append(min(values))
#                 humidity_max.append(max(values))
#             else:
#                 humidity_min.append(None)
#                 humidity_max.append(None)

#         # Return only precipitation + humidity
#         return JsonResponse({
#             "success": True,
#             "data": {
#                 "dates": daily.get("time", []),
#                 "rainfall_mm": daily.get("precipitation_sum", []),
#                 "humidity_min": humidity_min,
#                 "humidity_max": humidity_max,
#             }
#         })

#     except requests.exceptions.RequestException as e:
#         return JsonResponse({"success": False, "error": str(e)}, status=502)
#     except Exception as e:
#         return JsonResponse({"success": False, "error": str(e)}, status=500)

# Main crop price tracker
@api_view(['GET', 'POST'])
def crop_price_tracker(request):

    '''
    curl -X POST http://127.0.0.1:8000/api/crop_price_tracker/ \
-H "Content-Type: application/json" \
-d '{
  "crop": "Wheat",
  "state": "Maharashtra",
  "market": "Ulhasnagar"
}'

{"crops":["Alsandikai","Amaranthus","Amla(Nelli Kai)","Amphophalus","Apple","Arecanut(Betelnut/Supari)","Arhar (Tur/Red Gram)(Whole)","Ashgourd","Bajra(Pearl Millet/Cumbu)","Banana","Banana - Green","Beans","Beetroot","Bengal Gram Dal (Chana Dal)","Bengal Gram(Gram)(Whole)","Bhindi(Ladies Finger)","Bitter gourd","Black Gram (Urd Beans)(Whole)","Bottle gourd","Brinjal","Cabbage","Capsicum","Carrot","Castor Seed","Cauliflower","Chikoos(Sapota)","Chili Red","Chilly Capsicum","Cluster beans","Coconut","Coconut Oil","Coconut Seed","Colacasia","Coriander(Leaves)","Corriander seed","Cotton","Cowpea(Veg)","Cucumbar(Kheera)","Cummin Seed(Jeera)","Drumstick","Dry Fodder","Elephant Yam (Suran)","French Beans (Frasbean)","Garlic","Ginger(Dry)","Ginger(Green)","Grapes","Green Chilli","Green Gram (Moong)(Whole)","Green Peas","Ground Nut Seed","Groundnut","Groundnut (Split)","Guar","Guar Seed(Cluster Beans Seed)","Guava","Gur(Jaggery)","Indian Beans (Seam)","Isabgul (Psyllium)","Jowar(Sorghum)","Kabuli Chana(Chickpeas-White)","Knool Khol","Kulthi(Horse Gram)","Lak(Teora)","Lemon","Lentil (Masur)(Whole)","Lime","Linseed","Little gourd (Kundru)","Mahua","Maize","Mango (Raw-Ripe)","Mataki","Methi(Leaves)","Mint(Pudina)","Mousambi(Sweet Lime)","Mustard","Neem Seed","Onion","Onion Green","Orange","Paddy(Dhan)(Basmati)","Paddy(Dhan)(Common)","Papaya","Peas Wet","Peas cod","Pineapple","Pointed gourd (Parval)","Pomegranate","Potato","Pumpkin","Raddish","Rice","Ridgeguard(Tori)","Round gourd","Safflower","Seetapal","Sesamum(Sesame,Gingelly,Til)","Snakeguard","Soanf","Soyabean","Spinach","Sponge gourd","Sweet Potato","Sweet Pumpkin","Tapioca","Thondekai","Tinda","Tomato","Turmeric","Turmeric (raw)","Water Melon","Wheat","buttery"],"result":[],"error":"No data found for the given crop, state, and market."}%                                    


    '''


    crops = sorted({record['commodity'] for record in DATA if record.get('commodity')})
    result = []
    error = None

    if request.method == 'POST':
        crop = sanitize_input(request.data.get('crop', ''), 100)
        state = sanitize_input(request.data.get('state', ''), 100)
        market = sanitize_input(request.data.get('market', ''), 100)

        if not crop or not state or not market:
            error = "All fields (crop, state, market) are required."
        else:
            result = [
                r for r in DATA
                if r.get('commodity', '').lower() == crop.lower()
                and r.get('state', '').lower() == state.lower()
                and r.get('market', '').lower() == market.lower()
            ]
            if not result:
                error = "No data found for the given crop, state, and market."

    return Response({
        'crops': crops,
        'result': result,
        'error': error
    })

@api_view(['GET'])
def get_states(request):
    crop = sanitize_input(request.GET.get('crop', ''), 100).lower()
    if not crop:
        return Response([])
    states = sorted({r['state'] for r in DATA if r.get('commodity', '').lower() == crop})
    return Response(states)

@api_view(['GET'])
def get_markets(request):
    crop = sanitize_input(request.GET.get('crop', ''), 100).lower()
    state = sanitize_input(request.GET.get('state', ''), 100).lower()
    
    if not crop or not state:
        return Response([])
    
    markets = sorted({
        r['market'] for r in DATA
        if r.get('commodity', '').lower() == crop and r.get('state', '').lower() == state
    })
    return Response(markets)

@api_view(['GET'])
def soil_data(request, lat, lon):
    """
    Fetch soil data from Open-Meteo API
    """
    url = f"http://127.0.0.1:8000/soil/report?lat={lat}&lon={lon}"

    try:
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200 or "error" in data:
            return Response({"error": data.get("reason", "Failed to fetch soil data")}, status=response.status_code)

        soil_data = {
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "soil": data.get("soil", {})
        }

        return Response(data)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# @api_view(['GET'])
# def water_data(request, lat, lon):
#     url = f"{MEERSENS_URL}/water/current"
#     headers = {"apikey": MEERSENS_API_KEY}
#     params = {
#         "lat": lat,
#         "lng": lon,
#         "index_type": "meersens",
#         "health_recommendations": "true"
#     }
#     r = requests.get(url, headers=headers, params=params)
#     data = r.json()

#     if not data.get("found", True):
#         return JsonResponse({"message": "No water data available for this location."}, status=404)

#     return JsonResponse(data, safe=False, status=r.status_code)

# @csrf_exempt   # (disable CSRF for testing curl/postman; later use proper auth)
# def crop_recommendation_view(request):
#     if request.method == "POST":
#         try:
#             # Try JSON first
#             try:
#                 data = json.loads(request.body.decode("utf-8"))
#             except Exception:
#                 # Fallback to form-encoded
#                 data = request.POST

#             N = float(data.get("N"))
#             P = float(data.get("P"))
#             K = float(data.get("K"))
#             temperature = float(data.get("temperature"))
#             humidity = float(data.get("humidity"))
#             ph = float(data.get("ph"))
#             rainfall = float(data.get("rainfall"))

#             prediction = predict_crop(N, P, K, temperature, humidity, ph, rainfall)
#             return JsonResponse({"success": True, "prediction": prediction})
#         except Exception as e:
#             return JsonResponse({"success": False, "error": str(e)}, status=400)

#     return JsonResponse({"error": "Only POST allowed"}, status=405)

# @csrf_exempt
# def crop_yield_prediction(request):
#     '''
    
#     curl -X POST http://127.0.0.1:8000/api/crop-yield/ \        
# -H "Content-Type: application/json" \
# -d '{
#   "area": "Punjab",
#   "item": "Wheat",
#   "season": "Kharif",
#   "crop_year": 2025,
#   "average_rainfall": 200,
#   "pesticides": 5,
#   "annual_rainfall": 1800
# }'

# {"success": true, "prediction": 0.8999999761581421}%                                 

    
#     '''
#     if request.method != "POST":
#         return JsonResponse({"success": False, "error": "POST request required"}, status=400)

#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

#     result = predict_yield(data)
#     status_code = 200 if result.get("success") else 400
#     return JsonResponse(result, status=status_code)


# # @csrf_exempt
# # def fertilizer_recommendation(request):

# #     ''' 
# #     ENDPOINT REQUEST EXAMPLE (POSTMAN/CURL):

#     $ curl -X POST http://127.0.0.1:8000/api/fertilizer-recommendation/ \
# -H "Content-Type: application/json" \
# -d '{
#     "temperature": 30,
#     "humidity": 70,
#     "moisture": 25,
#     "soil_type": "Loamy",
#     "crop_type": "Wheat",
#     "nitrogen": 50,
#     "potassium": 30,
#     "phosphorous": 20
# }'

# {"success": true, "recommendation": "Urea"}%   
# ~ ⌚ 14:49:06
# $ curl https://api.groq.com/openai/v1/chat/completions \
#   -H "Content-Type: application/json" \
#   -H "Authorization: Bearer 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" \
#   -d '{
#     "model": "llama-3.1-8b-instant",
#     "messages": [
#       {"role": "system", "content": "You are a helpful assistant."},
#       {"role": "user", "content": "Explain how AI works in a few words."}
#     ],
#     "max_completion_tokens": 256
#   }'

# {"id":"chatcmpl-ba8597bd-e20b-43a3-9393-7c0b45f34bb0","object":"chat.completion","created":1757841538,"model":"llama-3.1-8b-instant","choices":[{"index":0,"message":{"role":"assistant","content":"AI works by processing data with algorithms to generate predictions or actions."},"logprobs":null,"finish_reason":"stop"}],"usage":{"queue_time":0.052068693,"prompt_tokens":51,"prompt_time":0.006643667,"completion_tokens":14,"completion_time":0.043850921,"total_tokens":65,"total_time":0.050494588},"usage_breakdown":null,"system_fingerprint":"fp_510c177af0","x_groq":{"id":"req_01k53rafjxfvqt5qhrem6rvvae"},"service_tier":"on_demand"}

# ~ ⌚ 14:49:07
# $ 



    
#     '''
    

#     if request.method != "POST":
#         return JsonResponse({"success": False, "error": "POST request required"}, status=400)
    
#     try:
        
#         data = json.loads(request.body.decode("utf-8"))
#         print("REQUEST BODY:", request.body)
#         print("PARSED DATA:", data)
#         temperature = float(data.get("temperature") or 0)
#         humidity = float(data.get("humidity") or 0)
#         moisture = float(data.get("moisture") or 0)
#         nitrogen = float(data.get("nitrogen") or 0)
#         potassium = float(data.get("potassium") or 0)
#         phosphorous = float(data.get("phosphorous") or 0)
#         soil_type = data.get("soil_type") or ""
#         crop_type = data.get("crop_type") or ""

        
#         # call your model
#         recommendation = predict_fertilizer(
#         temperature=temperature,  # ✅ fixed
#         humidity=humidity,
#         moisture=moisture,
#         soil_type=soil_type,
#         crop_type=crop_type,
#         nitrogen=nitrogen,
#         potassium=potassium,
#         phosphorous=phosphorous
# )

        
#         return JsonResponse({"success": True, "recommendation": recommendation})

#     except Exception as e:
#         return JsonResponse({"success": False, "error": str(e)}, status=400)


# # Initialize chatbot (do this once)
# # chatbot = ChatBot("FarmerBot")
# # trainer = ChatterBotCorpusTrainer(chatbot)
# # trainer.train("chatterbot.corpus.english")  # You can create your own corpus later

# # @csrf_exempt
# # def chat_with_bot(request):
# #     '''
# #     $ curl -X POST http://127.0.0.1:8000/api/chat/ \       
# # -H "Content-Type: application/json" \
# # -d '{"query": "Which crops are best for rainy season in Punjab?"}'

# # {"success": true, "reply": "Punjab is one of the most fertile regions in India, and the rainy season presents a unique set of opportunities for farmers. Here are some of the best crops that can be grown during the rainy season in Punjab:\n\n1. **Pulses**: Pulses, such as arhar (pigeon pea), moong (green gram), and urad (black gram), are ideal for the rainy season. They can grow in waterlogged conditions and are a great source of protein for livestock and human consumption.\n2. **Hybrid Rice**: Hybrid rice varieties, such as IR-64 and IR-72, are specifically designed to thrive in wet conditions and can be grown during the rainy season. They have a shorter maturity period and can produce high yields.\n3. **Sugarcane**: Sugarcane is another lucrative crop that can be grown during the rainy season. It's a drought-tolerant crop that can grow in waterlogged conditions, and its juice can be harvested and sold throughout the year.\n4. **Maize**: While maize is a crop that typically requires well-drained soil, there are some varieties that can tolerate waterlogging to a certain extent. These varieties can be grown during the rainy season, but it's essential to ensure proper drainage"}%
# #     '''
# #     if request.method != "POST":
# #         return JsonResponse({"success": False, "error": "POST method required."}, status=405)
        
# #     try:
# #         data = json.loads(request.body)
# #         user_query = data.get("query")
# #         if not user_query:
# #             return JsonResponse({"success": False, "error": "Missing 'query' field in request."}, status=400)

# #         # Customize system prompt for farmers
# #         system_prompt = (
# #             "You are an expert agricultural assistant. Answer farmers' questions clearly, "
# #             "give practical advice on crops, soil, irrigation, and weather, and avoid generic AI answers."
# #         )

# #         payload = {
# #             "model": MODEL_NAME,
# #             "messages": [
# #                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": user_query}
#             ],
#             "max_completion_tokens": 256
#         }

#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {GROQ_API_KEY}"
#         }

#         response = requests.post(GROQ_API_URL, headers=headers, json=payload)
#         response_data = response.json()

#         if response.status_code != 200:
#             return JsonResponse({"success": False, "error": response_data.get("error", "Unknown error")}, status=500)

#         # Extract the assistant's reply
#         reply = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
#         return JsonResponse({"success": True, "reply": reply})

#     except json.JSONDecodeError:
#         return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)
#     except Exception as e:
#         return JsonResponse({"success": False, "error": str(e)}, status=500)



