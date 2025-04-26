import os
import pickle
import re
import numpy as np

from extra_features import get_random_weather, is_rush_hour
from datetime import datetime, timedelta

# load model:
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ml_model", "model.pkl"))

with open(model_path, "rb") as file:
    model = pickle.load(file)

# station ID mapping:
station_to_id = {
    "norwich": 1,
    "london": 2,
    "cambridge": 3,
    "ipswich": 4,
    "manchester": 5
}


def parse_time_string(time_str):
    """Handle normal and casual time formats."""
    time_str = time_str.strip().lower()
    if "am" in time_str or "pm" in time_str:
        try:
            return datetime.strptime(time_str, "%I%p").hour
        except ValueError:
            return None
    elif "afternoon" in time_str:
        return 14
    elif "morning" in time_str:
        return 9
    elif ":" in time_str:
        try:
            return datetime.strptime(time_str, "%H:%M").hour
        except ValueError:
            return None
    return None


def extract_features_from_input(user_input):
    """
    Tries to extract origin, destination, time, and day from user input.
    Accepts casual formats like 'around 9am', 'today', 'tomorrow'.
    """

    user_input = user_input.lower()

    # here is where it will find origin and destination:
    origin = None
    destination = None
    for station in station_to_id.keys():
        if f"from {station}" in user_input:
            origin = station
        if f"to {station}" in user_input:
            destination = station

    if not origin or not destination:
        return None

    # finding time (like 9am, 14:00):
    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', user_input)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        ampm = time_match.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
    else:
        # Default to midday if not provided
        hour = 12

    # find day (monday, today, tomorrow):
    now = datetime.now()
    day_of_week = now.weekday()

    if "tomorrow" in user_input:
        day_of_week = (now + timedelta(days=1)).weekday()
    else:
        for idx, day in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            if day in user_input:
                day_of_week = idx
                break

    # calculation for station deviation:
    origin_id = station_to_id.get(origin)
    destination_id = station_to_id.get(destination)
    if origin_id is None or destination_id is None:
        return None

    station_deviation = abs(origin_id - destination_id)

    # peak time flag:
    peak = 1 if (7 <= hour <= 10 or 16 <= hour <= 19) else 0

    return np.array([[station_deviation, day_of_week, hour, peak]])


def predict_delay_from_input(user_input, weather=None):
    """Predict delay time based on extracted features."""
    features = extract_features_from_input(user_input)

    if features is None:
        return ("Sorry, I couldn't extract your train details. "
                "Please use something like 'from Norwich to London at 9am on Monday'.")

    prediction = model.predict(features)[0]

    if weather is None:
        weather = get_random_weather()

    extreme_conditions = {"heavy rain", "heavy snow", "thunderstorm", "stormy"}
    adjustment = 0

    if weather in extreme_conditions:
        adjustment += 5
    elif weather in {"sunny", "clear"}:
        adjustment -= 2

    # rush hour adjustment:
    hour = features[0][2]
    if is_rush_hour(hour):
        adjustment += 3

    # weekend adjustment:
    day_idx = features[0][1]
    if day_idx in (5, 6):
        adjustment += 1

    adjusted_prediction = max(prediction + adjustment, 0)
    minutes = int(adjusted_prediction)
    seconds = int(round((adjusted_prediction - minutes) * 60))
    return f"Predicted delay: {minutes} minutes and {seconds} seconds (weather: {weather})"
