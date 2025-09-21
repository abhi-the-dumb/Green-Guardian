from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from myapp.services.weather import weather_info
from myapp.services.weather import historical_weather
from myapp.services.weather import forecast
from myapp.services.weather import geocoding
from myapp.services.misc import aqi_info
from myapp.services.misc import water_data
from myapp.services.soil import get_soilgrids
from myapp.services.soil import fetch_soil_classification_view
from myapp.services.crops import crop_recommendation_view
from myapp.services.crops import crop_yield_prediction
from myapp.services.crops import fertilizer_recommendation
from myapp.services.crops import auto_fertilizer_recommendation
from myapp.services.crops import auto_crop_recommendation
from myapp.services.crops import crop_price_tracker
from myapp.services.misc import get_states
from myapp.services.misc import get_states
# from myapp.services.soil import soil_data
from myapp.services.soil import get_soilgrids
# from myapp.services.soil import get_soilgrids as soil_data
from myapp.services.soil import fetch_soil_classification_view
# from myapp.services.chat import chat_with_bot
from myapp.services.chat import get_chatbot_reply

urlpatterns = [
    path('weather/<str:city>/', weather_info, name='weather_info'),
    path('aqi/<str:lat>/<str:lon>/', aqi_info, name='aqi_info'),
    path('history/<str:lat>/<str:lon>/<str:start>/<str:end>/', historical_weather, name='history_info'),
    path('forecast/<str:lat>/<str:lon>/', forecast, name='forecast_info'),
    path('geocode/<str:city>/', geocoding, name='geocode_info'),
    path('crop_price_tracker/', crop_price_tracker, name='crop_price_tracker'),
    path('get_states/', get_states, name='get_states'),
    # path('get_markets/', get_markets, name='get_markets'),
    # path('soil/<str:lat>/<str:lon>/', soil_data, name='soil_data'),
    path('water/<str:lat>/<str:lon>/', water_data, name='water_data'),
    path('crop-recommendation/', csrf_exempt(crop_recommendation_view), name='crop_recommendation'),
    path('crop-yield/', crop_yield_prediction, name='crop_yield_prediction'),
    path('fertilizer-recommendation/', csrf_exempt(fertilizer_recommendation), name='fertilizer_recommendation'),
    path('chat/', get_chatbot_reply, name='chat_with_bot'),
    # path('pincode/<str:pincode>/', get_coordinates_from_pincode, name='get_coordinates_from_pincode'),
    path('get_soilgrids/<str:lat>/<str:lon>/', get_soilgrids, name='fetch_soilgrids'),
    path('get_soilclassification/<str:lat>/<str:lon>/', fetch_soil_classification_view, name='fetch_soil_classification'),
    path('auto-crop-recommendation/<str:lat>/<str:lon>/', csrf_exempt(auto_crop_recommendation), name='auto_crop_recommendation'),
    path('auto-fertilizer-recommendation/<str:lat>/<str:lon>/<str:crop_type>/', csrf_exempt(auto_fertilizer_recommendation), name='auto_fertilizer_recommendation'),
]
