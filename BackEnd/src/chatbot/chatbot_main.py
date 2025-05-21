# import random
# import re
# from train_chatbot import predict_delay_from_input
# from extra_features import get_train_crowd_info, get_random_weather
#
# # Predefined intents:
# intents = {
#     "intents": [
#         {
#             "tag": "greeting",
#             "patterns": ["hello", "hi", "hey"],
#             "responses": ["Hello!", "Hi there!", "Hey! How can I assist you today?"]
#         },
#         {
#             "tag": "goodbye",
#             "patterns": ["bye", "goodbye", "see you"],
#             "responses": ["Goodbye!", "See you next time!", "Take care!"]
#         },
#         {
#             "tag": "thanks",
#             "patterns": ["thank you", "thanks", "i appreciate it"],
#             "responses": ["You're welcome!", "No problem!", "Happy to help!"]
#         },
#         {
#             "tag": "name",
#             "patterns": ["what is your name", "who are you"],
#             "responses": ["I'm your train assistant chatbot.", "Call me TrainBot."]
#         },
#         {
#             "tag": "delay_prediction",
#             "patterns": [
#                 "train delay", "will my train be late", "predict delay", "delay prediction",
#                 "delay from", "any delay between", "delay info", "late train"
#             ],
#             "responses": []
#         }
#     ]
# }
#
#
# def match_intent(user_input):
#     """Match the user input to an intent tag."""
#     user_input = user_input.lower()
#     for intent in intents["intents"]:
#         for pattern in intent["patterns"]:
#             if pattern in user_input:
#                 return intent["tag"]
#
#     if "delay" in user_input or "train" in user_input:
#         return "delay_prediction"
#
#     return "unknown"
#
#
# def extract_train_info(text):
#     """Try to extract from/to, time, and day."""
#     pattern = r"from\s+(\w+)\s+to\s+(\w+).*?at\s+(\d{1,2}:\d{2}).*?on\s+(\w+)"
#     match = re.search(pattern, text.lower())
#     if match:
#         return {
#             "origin": match.group(1).capitalize(),
#             "destination": match.group(2).capitalize(),
#             "time": match.group(3),
#             "day": match.group(4).capitalize()
#         }
#     return None
#
#
# def generate_response(user_input):
#     """Generate a response based on user input."""
#     intent_tag = match_intent(user_input)
#
#     if intent_tag == "greeting":
#         return random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "greeting"][0])
#     elif intent_tag == "goodbye":
#         return random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "goodbye"][0])
#     elif intent_tag == "thanks":
#         return random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "thanks"][0])
#     elif intent_tag == "name":
#         return random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "name"][0])
#
#     elif intent_tag == "delay_prediction":
#         train_info = extract_train_info(user_input)
#         if train_info:
#             weather = get_random_weather()
#             delay = predict_delay_from_input(user_input, weather)
#             advice = get_train_crowd_info(user_input, weather)
#             return f"{delay}\n{advice}" if advice else delay
#         else:
#             return "Sorry, I couldn't extract the train journey details. Please use the format: 'from [origin] to [destination] at HH:MM on DAY'."
#
#     else:
#         return "Sorry, I don't understand. You can ask me things like:\n'predict delay from Norwich to London at 17:00 on Friday'"
#
#
# # Run chatbot
# if __name__ == "__main__":
#     print("Chatbot Test Mode (type 'exit' to stop)")
#     while True:
#         user_input = input("You: ")
#         if user_input.lower() == "exit":
#             print("Bot: Goodbye!")
#             break
#         response = generate_response(user_input)
#         print(f"Bot: {response}")

# imports:
import random
import re
import os
import requests
from datetime import datetime, timedelta
from train_chatbot import predict_delay_from_input
from extra_features import get_train_crowd_info, get_random_weather

# regex to extract origin, destination, time, and date (either dd/mm/yyyy or day-name)
DELAY_REGEX = re.compile(
    r"(?:delay\s+from|predict\s+delay\s+from|delay)\s+(.+?)\s+to\s+(.+?)"
    r"(?:\s+at\s+(\d{1,2}:\d{2}))?"
    r"(?:\s+on\s+(\d{1,2}/\d{1,2}/\d{2,4}|\w+))?",
    re.IGNORECASE
)
TICKET_REGEX = re.compile(
    r"(?:cheapest\s+ticket|ticket)\s+from\s+(.+?)\s+to\s+(.+?)"
    r"(?:\s+on\s+(\d{1,2}/\d{1,2}/\d{2,4}|\w+))?",
    re.IGNORECASE
)

# predefined intents:
intents = {
    "intents": [
        { "tag": "greeting", "patterns": ["hello", "hi", "hey"], "responses": ["hello!", "hi there!", "hey! how can i assist you today?"] },
        { "tag": "goodbye",  "patterns": ["bye", "goodbye", "see you"],        "responses": ["goodbye!", "see you next time!", "take care!"] },
        { "tag": "thanks",   "patterns": ["thank you", "thanks", "i appreciate it"], "responses": ["you're welcome!", "no problem!", "happy to help!"] },
        { "tag": "name",     "patterns": ["what is your name", "who are you"],    "responses": ["i'm your train assistant chatbot.", "call me trainbot."] },
        { "tag": "delay_prediction", "patterns": ["train delay", "will my train be late", "predict delay", "delay info", "late train"], "responses": [] },
        { "tag": "ticket_search",    "patterns": ["cheapest ticket", "ticket"],  "responses": [] }
    ]
}

# map day names to weekday numbers:
WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5,
    "sunday": 6
}

# helper to find next date for a weekday name:
def next_weekday(day_name: str) -> str:
    today = datetime.today()
    wd_target = WEEKDAYS.get(day_name.lower())
    if wd_target is None:
        return ""
    days_ahead = (wd_target - today.weekday() + 7) % 7 or 7
    return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

# function to match user input to intent:
def match_intent(user_input):
    u = user_input.lower()
    for intent in intents["intents"]:
        for pat in intent["patterns"]:
            if pat in u:
                return intent["tag"]
    # fallback: if mentions train or delay → delay_prediction
    if "delay" in u or "train" in u:
        return "delay_prediction"
    return "unknown"

# main response generator:
def generate_response(user_input):
    intent_tag = match_intent(user_input)

    # simple intents:
    if intent_tag in {"greeting", "goodbye", "thanks", "name"}:
        resp_list = next(i["responses"] for i in intents["intents"] if i["tag"] == intent_tag)
        return random.choice(resp_list)

    # ticket lookup:
    if intent_tag == "ticket_search":
        m = TICKET_REGEX.search(user_input)
        if not m:
            return ("sorry, please ask like:\n"
                    "'cheapest ticket from Norwich to London on Tuesday' "
                    "or 'cheapest ticket from Norwich to London on 15/06/2025'")
        orig, dest, date_str = m.groups()
        # parse date:
        if date_str and "/" in date_str:
            try:
                d = datetime.strptime(date_str, "%d/%m/%Y")
                travel_date = d.strftime("%Y-%m-%d")
            except ValueError:
                return "sorry, I couldn't understand that date. Use dd/mm/yyyy."
        elif date_str:
            travel_date = next_weekday(date_str)
            if not travel_date:
                return "sorry, I couldn't understand that day—use a weekday name or dd/mm/yyyy."
        else:
            return "please include a date or day: e.g. 'on Tuesday' or 'on 15/06/2025'."

        # call your tickets endpoint:
        api_url = os.environ.get("RAIL_API_URL")
        api_key = os.environ.get("RAIL_API_KEY")
        try:
            r = requests.get(f"{api_url}", params={
                "from": orig.strip(),
                "to":   dest.strip(),
                "date": travel_date,
                "apikey": api_key
            }, timeout=5)
            r.raise_for_status()
            info = r.json()
            return (f"Cheapest ticket from {orig.title()} to {dest.title()} on {travel_date} "
                    f"is £{info.get('price')} — book here: {info.get('bookingUrl')}")
        except Exception:
            return "sorry, I couldn't fetch ticket data right now."

    # delay prediction:
    if intent_tag == "delay_prediction":
        m = DELAY_REGEX.search(user_input)
        if not m:
            return ("sorry, please ask like:\n"
                    "'delay from Norwich to London at 15:30 on Tuesday'")
        orig, dest, time_str, day_str = m.groups()
        # build standard query:
        query = f"{orig.strip()} to {dest.strip()}"
        if time_str:
            query += f" at {time_str}"
        if day_str:
            # normalize day or leave as-is if it's a date
            if "/" not in day_str and day_str.lower() in WEEKDAYS:
                d = next_weekday(day_str)
                query += f" on {d}"
            else:
                query += f" on {day_str}"

        # get ML + extras:
        weather   = get_random_weather()
        delay_msg = predict_delay_from_input(query, weather)
        crowd_msg = get_train_crowd_info(query, weather)
        return f"{delay_msg}\n{crowd_msg}" if crowd_msg else delay_msg

    # fallback:
    return ("sorry, i don't understand. you can ask me things like:\n"
            "'delay from Norwich to London at 15:30 on Tuesday'\n"
            "'cheapest ticket from Norwich to London on 15/06/2025'")


