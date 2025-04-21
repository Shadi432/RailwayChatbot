import random

def is_rush_hour(hour):
    return 7 <= hour <= 10 or 16 <= hour <= 19

def is_public_holiday(day_str):
    return False  # Optional: replace with actual lookup

def get_random_weather():
    return random.choice([
        "sunny", "clear", "cloudy",
        "rainy", "heavy rain", "stormy", "heavy snow", "thunderstorm"
    ])

def get_train_crowd_info(user_input, weather=None):
    advice = []

    if weather is None:
        weather = get_random_weather()

    if weather in {"heavy rain", "heavy snow", "thunderstorm", "stormy"}:
        advice.append(f"The weather is {weather}, which may cause significant delays.")
    else:
        advice.append(f"The weather is {weather}, so no weather-induced disruptions are expected.")

    rush_hours = [str(h).zfill(2) for h in list(range(7, 11)) + list(range(16, 20))]
    if any(rh in user_input for rh in rush_hours):
        advice.append("It is rush hour, so trains might be crowded.")

    if "saturday" in user_input.lower() or "sunday" in user_input.lower():
        advice.append("Weekend schedules may differ; please check in advance.")

    return " ".join(advice)
