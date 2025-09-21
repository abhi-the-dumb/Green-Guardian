from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from services.soil import get_soilgrids , fetch_soil_classification as fetch_soil_classification_service, fetch_soil_classification_view as fetch_soil_classification_view_service # import your existing service function

@csrf_exempt
def soil_properties(request, lat, lon):
    return get_soilgrids(request, lat, lon)

@csrf_exempt
def fetch_soil_classification_view(request, lat, lon):
    return fetch_soil_classification_view_service(request, lat, lon)