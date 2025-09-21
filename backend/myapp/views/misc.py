from rest_framework.decorators import api_view
from django.http import JsonResponse
from services.misc import water_data as water_data_service, aqi_info as aqi_info_service  # import the service function

@api_view(['GET'])
def water_data(request, lat, lon):
    try:
        response = water_data_service(lat, lon)  # call the service
        return response  # this should already be a JsonResponse from the service
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@api_view(['GET'])
def aqi_info(request, lat, lon):
    try:
        response = aqi_info_service(lat, lon)  # call the service
        return response  # this should already be a JsonResponse from the service
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
