# imports:
import os
import pickle
import re
import numpy as np
from datetime import datetime
from extra_features import get_random_weather, is_rush_hour

# load trained model:
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ml_model", "model.pkl"))
with open(model_path, "rb") as file:
    model = pickle.load(file)

# load station mapping from training data:
data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../dataFile.txt"))

# read and get all unique stations:
station_df = np.genfromtxt(data_path, delimiter=",", dtype=str)
stations = set(station_df[:, 0]).union(set(station_df[:, 1]))
station_to_id = {station: idx for idx, station in enumerate(stations)}

# function to check peak hours:
def is_peak(hour):
    return 1 if (7 <= hour <= 10 or 16 <= hour <= 19) else 0

# function to extract features from user input:
def extract_features_from_input(user_input):
    user_input = user_input.lower()

    # pattern for natural queries:
    pattern = r"from\s+(\w+)\s+to\s+(\w+)(?:\s+at\s+(\d{1,2}:\d{2}))?(?:\s+on\s+(\w+))?"
    match = re.search(pattern, user_input)

    if not match:
        return None

    origin, destination, time_str, day_str = match.groups()

    origin = origin.upper()
    destination = destination.upper()

    # get current time if not provided:
    now = datetime.now()
    if not time_str:
        hour = now.hour
    else:
        try:
            hour = datetime.strptime(time_str, "%H:%M").hour
        except:
            return None

    # get current day if not provided:
    if not day_str:
        day_of_week = now.weekday()
    else:
        day_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
        }
        day_of_week = day_map.get(day_str.lower(), now.weekday())

    if origin not in station_to_id or destination not in station_to_id:
        return None

    station_deviation = abs(station_to_id[origin] - station_to_id[destination])
    peak = is_peak(hour)

    return np.array([[station_deviation, day_of_week, hour, peak]])

# main prediction function:
def predict_delay_from_input(user_input, weather=None, journey_info=None):
    """Predict train delay based on user input with improved NLP extraction."""
    from nlpprocessor import JourneyExtractor

    extractor = JourneyExtractor(debug=False)  # Ensure debug is False
    if journey_info is None:
        journey_info = extractor.extract_journey_details(user_input)
    
    if not journey_info or "origin" not in journey_info or "destination" not in journey_info:
        return ("Sorry, I couldn't extract your train journey details.\n"
                "Please use something like 'from BHM to EUS at 15:30 on Friday'.")
    
    origin = journey_info["origin"]
    destination = journey_info["destination"]
    
    # Get time from journey info or default to current hour
    time_str = journey_info.get("departure_time", "15:00")
    try:
        hour = int(time_str.split(":")[0])
    except:
        hour = 15  # Default
    
    # Get day from journey info or default to Friday
    day_str = journey_info.get("departure_day", "Friday")
    day_mapping = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2,
        "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6
    }
    day_of_week = day_mapping.get(day_str, 4)  # Default to Friday (4)
    
    # Create a synthetic query with all information for prediction
    synthetic_query = f"from {journey_info['origin']} to {journey_info['destination']}"
    if "departure_time" in journey_info and journey_info["departure_time"]:
        synthetic_query += f" at {journey_info['departure_time']}"
        time_str = journey_info["departure_time"]
    else:
        time_str = "12:00"  # Only use default if we know we've asked the user

    if "departure_day" in journey_info and journey_info["departure_day"]:
        synthetic_query += f" on {journey_info['departure_day']}"
        day_str = journey_info["departure_day"]
    else:
        day_str = "Friday"  # Only use default if we know we've asked the user
    
    # Get station deviation - AVOID USING PRINT FOR DEBUG
    try:
        # Instead of checking for existence first, use get() with default
        origin_id = station_to_id.get(origin, 0)
        dest_id = station_to_id.get(destination, 0)
        
        if origin_id == 0 or dest_id == 0:
            # Use a fallback estimation but DON'T print the debug message
            station_deviation = 5  # Some reasonable default
        else:
            station_deviation = abs(origin_id - dest_id)
            
        peak = is_peak(hour)
        
        features = np.array([[station_deviation, day_of_week, hour, peak]])
        
        # Suppress scikit-learn warnings
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Make prediction
            prediction = model.predict(features)[0]
        
        # Apply adjustments
        if weather is None:
            weather = get_random_weather()
            
        adjustment = 0
        if weather in {"heavy rain", "heavy snow", "thunderstorm", "stormy"}:
            adjustment += 5
        elif weather in {"sunny", "clear"}:
            adjustment -= 2
            
        if is_rush_hour(hour):
            adjustment += 3
            
        if day_of_week in (5, 6):  # Weekend adjustment
            adjustment += 1
            
        adjusted = max(prediction + adjustment, 0)
        minutes = int(adjusted)
        seconds = int(round((adjusted - minutes) * 60))
        
        origin_name = origin
        dest_name = destination
        
        return f"Predicted delay for your journey from {origin_name} to {dest_name} at {time_str} on {day_str}: {minutes} minutes and {seconds} seconds (Weather: {weather})"
        
    except Exception as e:
        # Don't print the debug error message
        return f"Sorry, I encountered an error while processing your request. Please try again with a different query."
