import random
from train_chatbot import predict_delay_from_input
from extra_features import get_train_crowd_info, get_random_weather

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
            "patterns": ["train delay", "will my train be late", "predict delay", "delay prediction", "what is the delay"],
            "responses": []
        }
    ]
}


def match_intent(user_input):
    """Find matching intent from the user input."""
    user_input = user_input.lower()
    for intent in intents["intents"]:
        for pattern in intent["patterns"]:
            if pattern in user_input:
                return intent["tag"]

    if "delay" in user_input or "train" in user_input:
        return "delay_prediction"

    return "unknown"


def generate_response(user_input):
    """Generate a response based on the detected intent."""
    intent_tag = match_intent(user_input)

    if intent_tag in {"greeting", "goodbye", "thanks", "name"}:
        intent_data = next(i for i in intents["intents"] if i["tag"] == intent_tag)
        response = random.choice(intent_data["responses"])
    elif intent_tag == "delay_prediction":
        weather = get_random_weather()
        response = predict_delay_from_input(user_input, weather)
        extra_info = get_train_crowd_info(user_input, weather)
        if extra_info:
            response += "\n" + extra_info
    else:
        response = "Sorry, I don't understand."

    return response


if __name__ == "__main__":
    print("Chatbot Test Mode (type 'exit' to stop)")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Bot: Goodbye!")
            break
        response = generate_response(user_input)
        print(f"Bot: {response}")
