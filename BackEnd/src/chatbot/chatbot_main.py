import random
import re
from train_chatbot import predict_delay_from_input
from extra_features import get_train_crowd_info, get_random_weather
from nlpprocessor import JourneyExtractor


# Predefined intents:
intents = {
    "intents": [
        {
            "tag": "greeting",
            "patterns": ["hello", "hi", "hey"],
            "responses": ["Hello!", "Hi there!", "Hey! How can I assist you today?"]
        },
        {
            "tag": "goodbye",
            "patterns": ["bye", "goodbye", "see you"],
            "responses": ["Goodbye!", "See you next time!", "Take care!"]
        },
        {
            "tag": "thanks",
            "patterns": ["thank you", "thanks", "i appreciate it"],
            "responses": ["You're welcome!", "No problem!", "Happy to help!"]
        },
        {
            "tag": "name",
            "patterns": ["what is your name", "who are you"],
            "responses": ["I'm your train assistant chatbot.", "Call me TrainBot."]
        },
        {
            "tag": "delay_prediction",
            "patterns": [
                "train delay", "will my train be late", "predict delay", "delay prediction",
                "delay from", "any delay between", "delay info", "late train"
            ],
            "responses": []
        }
    ]
}

journey_extractor = JourneyExtractor()


def match_intent(user_input):
    """Match the user input to an intent tag."""
    user_input = user_input.lower()
    for intent in intents["intents"]:
        for pattern in intent["patterns"]:
            if pattern in user_input:
                return intent["tag"]

    if "delay" in user_input or "train" in user_input:
        return "delay_prediction"

    return "unknown"


def extract_train_info(text):
    """Extract train journey information from the text."""
    # Use the JourneyExtractor class to extract information
    journey_info = journey_extractor.extract_journey_details(text)
    if journey_info:
        return {
            "origin": journey_info.get("origin"),
            "destination": journey_info.get("destination"),
            "time": journey_info.get("departure_time"),  
            "day": journey_info.get("departure_day")     
        }
    return None

    # Alternative regex-based extraction (commented out)
   # """Try to extract from/to, time, and day."""
    #pattern = r"from\s+(\w+)\s+to\s+(\w+).*?at\s+(\d{1,2}:\d{2}).*?on\s+(\w+)"
    #match = re.search(pattern, text.lower())
    #if match:
        #return {
       #     "origin": match.group(1).capitalize(),
        #    "destination": match.group(2).capitalize(),
       #    "time": match.group(3),
        #    "day": match.group(4).capitalize()
        #}
    #return None


def generate_response(user_input):
    """Generate a response based on user input."""
    intent_tag = match_intent(user_input)

    if intent_tag == "greeting":
        return random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "greeting"][0])
    elif intent_tag == "goodbye":
        return random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "goodbye"][0])
    elif intent_tag == "thanks":
        return random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "thanks"][0])
    elif intent_tag == "name":
        return random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "name"][0])

    elif intent_tag == "delay_prediction":
        train_info = extract_train_info(user_input)
        if train_info:
            weather = get_random_weather()
            delay = predict_delay_from_input(user_input, weather)
            advice = get_train_crowd_info(user_input, weather)
            return f"{delay}\n{advice}" if advice else delay
        else:
            return "Sorry, I couldn't extract the train journey details. Please use the format: 'from [origin] to [destination] at HH:MM on DAY'."

    else:
        return "Sorry, I don't understand. You can ask me things like:\n'predict delay from Norwich to London at 17:00 on Friday'"


# Run chatbot
if __name__ == "__main__":
    print("Chatbot Test Mode (type 'exit' to stop)")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Bot: Goodbye!")
            break
        response = generate_response(user_input)
        print(f"Bot: {response}")
