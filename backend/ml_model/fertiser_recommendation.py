import os
import joblib
import pandas as pd

# Get the root of the backend folder
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/ml_model -> backend
MODELS_DIR = os.path.join(BACKEND_DIR, 'models_store')

# Debug: check the resolved path
print("Loading model from:", os.path.join(MODELS_DIR, 'fertilizer_model.pkl'))

# Load model and encoders
model = joblib.load(os.path.join(MODELS_DIR, 'fertilizer_model.pkl'))
soil_encoder = joblib.load(os.path.join(MODELS_DIR, 'soil_encoder.pkl'))
crop_encoder = joblib.load(os.path.join(MODELS_DIR, 'fertilizer_recommendation_crop_encoder.pkl'))
fertilizer_encoder = joblib.load(os.path.join(MODELS_DIR, 'fertilizer_encoder.pkl'))

def decode_fertilizer(encoded_label):
    return fertilizer_encoder.inverse_transform([encoded_label])[0]

def show_available_classes():
    print("Soil types:", soil_encoder.classes_)
    print("Crop types:", crop_encoder.classes_)
    print("Fertilizer types:", fertilizer_encoder.classes_)

def predict_fertilizer(temperature, humidity, moisture, soil_type, crop_type, nitrogen, potassium, phosphorous):
    # Encode categorical inputs
    soil_encoded = soil_encoder.transform([soil_type])[0]
    crop_encoded = crop_encoder.transform([crop_type])[0]

    # Prepare input DataFrame
    input_data = pd.DataFrame([[
        temperature, humidity, moisture,
        soil_encoded, crop_encoded,
        nitrogen, potassium, phosphorous
    ]], columns=[
        'Temparature', 'Humidity ', 'Moisture',
        'Soil Type', 'Crop Type',
        'Nitrogen', 'Potassium', 'Phosphorous'
    ])

    # Predict
    pred = model.predict(input_data)[0]
    return decode_fertilizer(pred)

# 👇 Run this once to see which soil/crop/fertilizer types your model knows
show_available_classes()
