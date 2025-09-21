from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from services.crops import fertilizer_recommendation as service_fertilizer_recommendation, crop_yield_prediction as service_crop_yield_prediction, crop_recommendation_view as crop_recommendation_service, auto_fertilizer_recommendation as service_auto_fertilizer_recommendation, auto_crop_recommendation as service_auto_crop_recommendation, crop_price_tracker as service_crop_price_tracker  

@csrf_exempt
def fertilizer_recommendation(request):
    return service_fertilizer_recommendation(request)

@csrf_exempt
def crop_yield_prediction(request):
    return service_crop_yield_prediction(request)

@csrf_exempt
def crop_recommendation_view(request):
    return crop_recommendation_service(request)

@csrf_exempt
def auto_fertilizer_recommendation(request, lat, lon, crop_type):
    return service_auto_fertilizer_recommendation(request, lat, lon, crop_type)

@csrf_exempt
def auto_crop_recommendation(request, lat, lon):
    return service_auto_crop_recommendation(request, lat, lon)

@csrf_exempt
def crop_price_tracker(request):
    return service_crop_price_tracker(request)
