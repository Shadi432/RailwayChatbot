import os
import pickle
import re
import numpy as np
from datetime import datetime
from extra_features import get_random_weather, is_rush_hour

# Dynamically resolve the absolute path to the model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml_model", "model.pkl"))

# Load the trained model
with open(model_path, "rb") as file:
    model = pickle.load(file)


def is_peak(hour):
    """Return 1 if the hour is in peak time, else 0."""
    return 1 if (7 <= hour <= 10 or 16 <= hour <= 19) else 0


# Simple station mapping (demo):
station_to_id = {
    "norwich": 1,
    "london": 2,
    "cambridge": 3,
    "ipswich": 4,
    "manchester": 5
}


def extract_features_from_input(user_input):
    """
    Extracts features (station deviation, day of week, hour, on-peak) from user input.
    Expects a format like: "from London to Norwich at 12:00 on Saturday"
    """
    pattern = r".*from\s+([\w\s]+?)\s+to\s+([\w\s]+?)\s+at\s+(\d{1,2}:\d{2}).*on\s+(\w+).*"
    match = re.search(pattern, user_input.lower())
    if not match:
        return None

    origin, destination, time_str, day_str = match.groups()
    origin = origin.strip()
    destination = destination.strip()

    try:
        time_obj = datetime.strptime(time_str, "%H:%M")
        hour = time_obj.hour
    except Exception as e:
        print(f"Time parsing error: {e}")
        return None

    day_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    if day_str not in day_map:
        return None

    if origin not in station_to_id or destination not in station_to_id:
        return None

    origin_id = station_to_id[origin]
    dest_id = station_to_id[destination]
    station_deviation = abs(origin_id - dest_id)
    day_of_week = day_map[day_str]
    peak = is_peak(hour)

    return np.array([[station_deviation, day_of_week, hour, peak]])


def predict_delay_from_input(user_input, weather=None):
    """
    Extracts features from user input and uses the ML model to predict train delay.
    Applies adjustments based on weather, rush hour, and weekend.
    Returns the prediction in minutes and seconds.
    """
    features = extract_features_from_input(user_input)
    if features is None:
        return ("Sorry, I couldn't extract the train journey details. "
                "Please use the format: 'from [origin] to [destination] at HH:MM on DAY'.")

    # Base prediction from the model (in minutes, as a float)
    prediction = model.predict(features)[0]

    # Use provided weather or generate one
    if weather is None:
        weather = get_random_weather()

    # Adjust prediction based on weather
    extreme_conditions = {"heavy rain", "heavy snow", "thunderstorm", "stormy"}
    adjustment = 0
    if weather in extreme_conditions:
        # Increase delay by 5 minutes for extreme weather:
        adjustment += 5
    elif weather in {"sunny", "clear"}:
        # Decrease delay by 2 minutes if weather is fine:
        adjustment -= 2

    # Check for rush hour using regex on the user input:
    time_match = re.search(r'(\d{1,2}):(\d{2})', user_input)
    if time_match:
        hour = int(time_match.group(1))
        if is_rush_hour(hour):
            # Add 3 minutes for rush hour:
            adjustment += 3

    # Check for weekend keywords in the input:
    if "saturday" in user_input.lower() or "sunday" in user_input.lower():
        # Add 1 minute for weekend:
        adjustment += 1

    adjusted_prediction = max(prediction + adjustment, 0)
    minutes = int(adjusted_prediction)
    seconds = int(round((adjusted_prediction - minutes) * 60))
    return f"Predicted delay: {minutes} minutes and {seconds} seconds (weather: {weather})"