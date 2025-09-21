from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from django.core.cache import cache

import os
import requests

load_dotenv()

SOILGRIDS_PROPERTIES_URL = os.getenv(
    "SOILGRIDS_PROPERTIES_URL", "https://rest.isric.org/soilgrids/v2.0/properties/query"
)
SOILGRIDS_CLASSIFICATION_URL = os.getenv(
    "SOILGRIDS_CLASSIFICATION_URL", "https://rest.isric.org/soilgrids/v2.0/classification/query"
)

def fetch_soilgrids(lat: float, lon: float):
    params = {
        "lat": lat,
        "lon": lon,
        "property": [
            "bdod", "cec", "cfvo", "clay", "nitrogen", "ocd", "ocs",
            "phh2o", "sand", "silt", "soc", "wv0010", "wv0033", "wv1500"
        ],
        "depth": [
            "0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm",
            "100-200cm", "0-30cm"
        ],
        "value": ["Q0.5", "Q0.05", "Q0.95", "mean", "uncertainty"]
    }

    cache_key = f"soil_{lat}_{lon}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        resp = requests.get(SOILGRIDS_PROPERTIES_URL, params=params, timeout=20)
        resp.raise_for_status()   # raises error on bad status
        data = resp.json()
        cache.set(cache_key, data, timeout=60*60*24)  # cache for 1 day
        return data
    except requests.exceptions.Timeout:
        # fallback if API is too slow
        return {}
    except Exception as e:
        return {"error": str(e)}

@csrf_exempt
def get_soilgrids(request, lat, lon):
    try:
        lat = float(lat)
        lon = float(lon)
        raw_data = fetch_soilgrids(lat, lon)

        properties = raw_data.get("properties", {})
        def extract_single_value(prop_name, depth_label="0-5cm", stat="mean"):
            layers = properties.get("layers", [])
            for layer in layers:
                if layer.get("name") == prop_name:
                    for d in layer.get("depths", []):
                        if d.get("label") == depth_label:
                            return d.get("values", {}).get(stat)
            return None



        filtered = {
            "nitrogen": extract_single_value("nitrogen"),
            "soil_moisture": {
                "wv0033": extract_single_value("wv0033"),
                "wv1500": extract_single_value("wv1500"),
            },
            "ph": extract_single_value("phh2o"),
        }

        classification = fetch_soil_classification(lat, lon)
        filtered["soil_type"] = classification.get("wrb_class_name")

        return JsonResponse(filtered, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def extract(props, soil_data, depth="0-5cm", stat="mean"):
    if isinstance(props, str):
        props = [props]
    for layer in soil_data.get("properties", {}).get("layers", []):
        for prop in props:
            if prop in layer.get("name", "").lower():
                for d in layer.get("depths", []):
                    if depth in d.get("label", ""):
                        values = d.get("values", {})
                        return values.get(stat) or list(values.values())[0]
    return None

def fetch_soil_classification(lat: float, lon: float):
    params = {"lat": lat, "lon": lon, "number_classes": 5}
    resp = requests.get(SOILGRIDS_CLASSIFICATION_URL, params=params, timeout=30)
    return resp.json()

@csrf_exempt
def fetch_soil_classification_view(request, lat, lon):
    try:
        lat = float(lat)
        lon = float(lon)
        data = fetch_soil_classification(lat, lon)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
