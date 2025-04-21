import os
import pickle
import re
import numpy as np
from datetime import datetime
from extra_features import get_random_weather, is_rush_hour

# Load trained model
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ml_model", "model.pkl"))
with open(model_path, "rb") as file:
    model = pickle.load(file)

# Station mapping (demo)
station_to_id = {
    "norwich": 1,
    "london": 2,
    "cambridge": 3,
    "ipswich": 4,
    "manchester": 5
}

def is_peak(hour):
    return 1 if (7 <= hour <= 10 or 16 <= hour <= 19) else 0

def extract_features_from_input(user_input):
    pattern = r".*from\s+([\w\s]+?)\s+to\s+([\w\s]+?)\s+at\s+(\d{1,2}:\d{2}).*on\s+(\w+).*"
    match = re.search(pattern, user_input.lower())
    if not match:
        return None

    origin, destination, time_str, day_str = match.groups()
    origin = origin.strip()
    destination = destination.strip()

    try:
        hour = datetime.strptime(time_str, "%H:%M").hour
    except:
        return None

    day_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }

    if day_str not in day_map:
        return None
    if origin not in station_to_id or destination not in station_to_id:
        return None

    station_deviation = abs(station_to_id[origin] - station_to_id[destination])
    return np.array([[station_deviation, day_map[day_str], hour, is_peak(hour)]])

def predict_delay_from_input(user_input, weather=None):
    features = extract_features_from_input(user_input)
    if features is None:
        return "Sorry, I couldn't extract the train journey details. Please use the format: 'from [origin] to [destination] at HH:MM on DAY'."

    prediction = model.predict(features)[0]

    if weather is None:
        weather = get_random_weather()

    adjustment = 0
    if weather in {"heavy rain", "heavy snow", "thunderstorm", "stormy"}:
        adjustment += 5
    elif weather in {"sunny", "clear"}:
        adjustment -= 2

    if re.search(r'(\d{1,2}):(\d{2})', user_input):
        hour = int(re.search(r'(\d{1,2}):(\d{2})', user_input).group(1))
        if is_rush_hour(hour):
            adjustment += 3

    if "saturday" in user_input.lower() or "sunday" in user_input.lower():
        adjustment += 1

    adjusted = max(prediction + adjustment, 0)
    minutes = int(adjusted)
    seconds = int(round((adjusted - minutes) * 60))
    return f"Predicted delay: {minutes} minutes and {seconds} seconds (weather: {weather})"
