from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

# Import the functions from your services module
from services.weather import historical_weather as hw_service, forecast as forecast_service, weather_info as weather_info_service, geocoding as geocoding_service   


@api_view(['GET'])
def historical_weather(request, lat, lon, start, end):
    return hw_service(request, lat, lon, start, end)

@api_view(['GET'])
def forecast(request, lat, lon):
    return forecast_service(request, lat, lon)

@api_view(['GET'])
def weather_info(request, city):
    return weather_info_service(request, city)

@api_view(['GET'])
def geocoding(request, city):
    return geocoding_service(request, city)