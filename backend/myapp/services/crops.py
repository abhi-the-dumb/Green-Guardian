import json
import re
import requests

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from rest_framework.decorators import api_view
from rest_framework.response import Response

# Your ML models
from ml_model.fertiser_recommendation import predict_fertilizer
from ml_model.crop_yield_predictor import predict_yield
from ml_model.crop_recommendation import predict_crop

# Utilities for soil/weather extraction (you need to implement these)
from .soil import fetch_soilgrids, extract
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

API_URL = os.getenv("CROP_PRICE_API_URL", "API_KEY_DATA_URL")    
API_PARAMS = {
    "api-key": os.getenv("CROP_PRICE_API_KEY", "API_KEY_DATA"),
    "format": "json",
    "limit": 1000
}

def load_data():
    try:
        response = requests.get(API_URL, params=API_PARAMS, timeout=10)
        response.raise_for_status()
        return response.json().get("records", [])
    except requests.RequestException as e:
        print(f"API request failed: {str(e)}")
        return []

DATA = load_data()

@csrf_exempt
def fertilizer_recommendation(request):

    ''' 
    ENDPOINT REQUEST EXAMPLE (POSTMAN/CURL):

    $ curl -X POST http://127.0.0.1:8000/api/fertilizer-recommendation/ \
-H "Content-Type: application/json" \
-d '{
    "temperature": 30,
    "humidity": 70,
    "moisture": 25,
    "soil_type": "Loamy",
    "crop_type": "Wheat",
    "nitrogen": 50,
    "potassium": 30,
    "phosphorous": 20
}'

{"success": true, "recommendation": "Urea"}%   

'''
    

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST request required"}, status=400)
    
    try:
        
        data = json.loads(request.body.decode("utf-8"))
        print("REQUEST BODY:", request.body)
        print("PARSED DATA:", data)
        temperature = float(data.get("temperature") or 0)
        humidity = float(data.get("humidity") or 0)
        moisture = float(data.get("moisture") or 0)
        nitrogen = float(data.get("nitrogen") or 0)
        potassium = float(data.get("potassium") or 0)
        phosphorous = float(data.get("phosphorous") or 0)
        soil_type = data.get("soil_type") or ""
        crop_type = data.get("crop_type") or ""

        
        # call your model
        recommendation = predict_fertilizer(
        temperature=temperature,  # ✅ fixed
        humidity=humidity,
        moisture=moisture,
        soil_type=soil_type,
        crop_type=crop_type,
        nitrogen=nitrogen,
        potassium=potassium,
        phosphorous=phosphorous
)

        
        return JsonResponse({"success": True, "recommendation": recommendation})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@csrf_exempt
def crop_yield_prediction(request):
    '''
    
    curl -X POST http://127.0.0.1:8000/api/crop-yield/ \        
-H "Content-Type: application/json" \
-d '{
  "area": "Punjab",
  "item": "Wheat",
  "season": "Kharif",
  "crop_year": 2025,
  "average_rainfall": 200,
  "pesticides": 5,
  "annual_rainfall": 1800
}'

{"success": true, "prediction": 0.8999999761581421}%                                 

    
    '''
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST request required"}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    result = predict_yield(data)
    status_code = 200 if result.get("success") else 400
    return JsonResponse(result, status=status_code)

@csrf_exempt
def crop_recommendation_view(request):
    if request.method == "POST":
        try:
            # Try JSON first
            try:
                data = json.loads(request.body.decode("utf-8"))
            except Exception:
                # Fallback to form-encoded
                data = request.POST

            N = float(data.get("N"))
            P = float(data.get("P"))
            K = float(data.get("K"))
            temperature = float(data.get("temperature"))
            humidity = float(data.get("humidity"))
            ph = float(data.get("ph"))
            rainfall = float(data.get("rainfall"))

            prediction = predict_crop(N, P, K, temperature, humidity, ph, rainfall)
            return JsonResponse({"success": True, "prediction": prediction})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    return JsonResponse({"error": "Only POST allowed"}, status=405)

@csrf_exempt
def auto_fertilizer_recommendation(request, lat, lon, crop_type):
    '''
    $ curl http://127.0.0.1:8000/api/auto-fertilizer-recommendation/15.3/75.2/Maize/

{"success": true, "inputs": {"crop": "Maize", "N": 153, "P": 20, "K": 30, "temperature": 24.75, "humidity": 85.79166666666667, "rainfall": 1.6}, "recommendation": "Urea"}%   
'''
    try:
        lat = float(lat)
        lon = float(lon)

        # 1. Get Soil Data
        soil_raw = fetch_soilgrids(lat, lon)
        N = extract(["nitrogen", "nitrogen_tot"], soil_raw)
        P = extract(["phosphorus", "phosphorus_tot"], soil_raw) or 20
        K = extract(["potassium", "potassium_tot"], soil_raw) or 30
        ph = extract(["phh2o", "ph"], soil_raw)

        if N is None or ph is None:
            return JsonResponse({"error": "Insufficient soil data"}, status=500)

        # 2. Get Weather Data (Open-Meteo)
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&hourly=relativehumidity_2m"
            f"&forecast_days=1&timezone=auto"
        )
        weather_resp = requests.get(forecast_url, timeout=10).json()

        daily = weather_resp.get("daily", {})
        hourly = weather_resp.get("hourly", {})

        # Temperature
        temperature = None
        if "temperature_2m_max" in daily and "temperature_2m_min" in daily:
            temperature = (daily["temperature_2m_max"][0] + daily["temperature_2m_min"][0]) / 2

        # Rainfall
        rainfall = daily.get("precipitation_sum", [None])[0]

        # Humidity
        humidity = None
        if "time" in hourly and "relativehumidity_2m" in hourly and daily.get("time"):
            today = daily["time"][0]
            values = [h for t, h in zip(hourly["time"], hourly["relativehumidity_2m"]) if t.startswith(today)]
            if values:
                humidity = sum(values) / len(values)

        if None in [temperature, humidity, rainfall]:
            return JsonResponse({"error": "Weather data missing"}, status=500)

        # 3. Call Fertilizer Model (or Rule-Based System)
        recommendation = predict_fertilizer(
            temperature=temperature,
            humidity=humidity,
            # ph=ph,
            moisture = 20,
            soil_type="Loamy",   # TODO: replace with soil classification if available
            crop_type=crop_type,
            nitrogen=N,
            phosphorous=P,
            potassium=K,
            # rainfall=rainfall
        )

        return JsonResponse({
            "success": True,
            "inputs": {
                "crop": crop_type,
                "N": N, "P": P, "K": K,
                "temperature": temperature,
                "humidity": humidity,
                # "ph": ph,
                "rainfall": rainfall
            },
            "recommendation": recommendation
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def auto_crop_recommendation(request, lat, lon):
    '''
    $ curl http://127.0.0.1:8000/api/auto-crop-recommendation/15.3/75.2/            

{"success": true, "inputs": {"N": 50, "P": 20, "K": 30, "temperature": 24.75, "humidity": 85.79166666666667, "ph": 6.5, "rainfall": 1.6}, "prediction": "muskmelon"}% 
'''
    try:
        lat = float(lat)
        lon = float(lon)

        # 1. Get Soil Data
        soil_raw = fetch_soilgrids(lat, lon)
        nitrogen = extract(["nitrogen", "nitrogen_tot"], soil_raw) or 50
        ph = extract(["phh2o", "ph"], soil_raw) or 6.5

        if nitrogen is None or ph is None:
            return JsonResponse({"error": "Insufficient soil data"}, status=500)

        # 2. Get Weather Data (Open-Meteo)
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&hourly=relativehumidity_2m"
            f"&forecast_days=1&timezone=auto"
        )
        weather_resp = requests.get(forecast_url, timeout=10).json()

        daily = weather_resp.get("daily", {})
        hourly = weather_resp.get("hourly", {})

        # Temperature
        temperature = None
        if "temperature_2m_max" in daily and "temperature_2m_min" in daily:
            temperature = (daily["temperature_2m_max"][0] + daily["temperature_2m_min"][0]) / 2

        # Rainfall
        rainfall = daily.get("precipitation_sum", [None])[0]

        # Humidity (average of today’s hourly values)
        humidity = None
        if "time" in hourly and "relativehumidity_2m" in hourly and daily.get("time"):
            today = daily["time"][0]
            values = [h for t, h in zip(hourly["time"], hourly["relativehumidity_2m"]) if t.startswith(today)]
            if values:
                humidity = sum(values) / len(values)

        if None in [temperature, humidity, rainfall]:
            return JsonResponse({"error": "Weather data missing"}, status=500)

        # 3. Run ML Crop Recommendation
        P = 20  # TODO: replace with real phosphorus
        K = 30  # TODO: replace with real potassium

        crop = predict_crop(nitrogen, P, K, temperature, humidity, ph, rainfall)

        return JsonResponse({
            "success": True,
            "inputs": {
                "N": nitrogen, "P": P, "K": K,
                "temperature": temperature,
                "humidity": humidity,
                "ph": ph,
                "rainfall": rainfall
            },
            "prediction": crop
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def sanitize_input(text, max_length=255):
    """Sanitize string input for safety."""
    if not isinstance(text, str):
        return ""
    # Remove potentially dangerous characters
    cleaned = re.sub(r'[<>"\']', '', text.strip())
    return cleaned[:max_length]

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