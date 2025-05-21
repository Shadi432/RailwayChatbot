# imports:
import random
import re
import uuid
import time
import warnings
import requests
from train_chatbot import predict_delay_from_input
from extra_features import get_train_crowd_info, get_random_weather
from nlpprocessor import JourneyExtractor  # Import JourneyExtractor for NLP
from flask import jsonify  # Import jsonify for Flask response
from station_dicts import STATION_CODES, STATION_NAME_TO_CODE  # <-- Make sure this import is at the top

warnings.filterwarnings("ignore")  # Suppress warnings

# Initialize the JourneyExtractor with debug off
journey_extractor = JourneyExtractor(debug=False)

# Global conversation memory
conversation_history = {}
active_conversations = {}

# predefined intents:
intents = {
    "intents": [
        {
            "tag": "greeting",
            "patterns": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"],
            "responses": ["Hello! I can help with train information and delay predictions. How can I assist you today?", 
                          "Hi there! I'm your railway assistant. Need help with train times or delays?", 
                          "Hey! Looking for train information today?"]
        },
        {
            "tag": "goodbye",
            "patterns": ["bye", "goodbye", "see you", "that's all", "exit"],
            "responses": ["Goodbye! Have a safe journey!", 
                          "See you next time! Safe travels!", 
                          "Thanks for chatting. Have a great day!"]
        },
        {
            "tag": "thanks",
            "patterns": ["thank you", "thanks", "i appreciate it", "great help"],
            "responses": ["You're welcome! Is there anything else I can help with?", 
                          "No problem! Need help with anything else?", 
                          "Happy to help! Let me know if you need more information."]
        },
        {
            "tag": "name",
            "patterns": ["what is your name", "who are you", "what should I call you"],
            "responses": ["I'm your railway assistant chatbot. You can call me RailBot!", 
                          "My name is RailBot, your digital railway assistant.", 
                          "I'm RailBot! Here to help with all your railway questions."]
        },
        {
            "tag": "delay_prediction",
            "patterns": [
                "train delay", "will my train be late", "predict delay", "delay prediction",
                "delay from", "any delay between", "delay info", "late train", "on time"
            ],
            "responses": []
        },
        {
            "tag": "ticket_price",
            "patterns": [
                "ticket price", "how much", "fare", "cost", "ticket cost",
                "buy ticket", "purchase", "book", "cheapest", "cheap ticket",
                "ticket fare", "how much is a ticket", "price"
            ],
            "responses": []
        },
        {
            "tag": "help",
            "patterns": ["help", "what can you do", "how does this work", "features", "commands"],
            "responses": [
                "I can help you with:\n• Train delay predictions\n• Ticket price information\n• Journey planning\n\nJust ask me questions like:\n'Will my train from London to Manchester be delayed?'\n'How much is an adult single ticket from Norwich to London?'\n'What's the price of an off-peak return to Birmingham?'"
            ]
        },
        {
            "tag": "book_ticket",
            "patterns": [
                "book", "buy", "purchase", "reserve", "get ticket",
                "i need to book a ticket", "i want to book", "can i book", "book a train", "book a ticket"
            ],
            "responses": []
        }
    ]
}

# Define conversation states
CONVERSATION_STATES = {
    "GREETING": "GREETING",
    "COLLECTING_ORIGIN": "COLLECTING_ORIGIN",
    "COLLECTING_DESTINATION": "COLLECTING_DESTINATION",
    "COLLECTING_TIME": "COLLECTING_TIME", 
    "COLLECTING_DAY": "COLLECTING_DAY",
    "COLLECTING_TICKET_TYPE": "COLLECTING_TICKET_TYPE",   # single/return
    "COLLECTING_TICKET_TIME": "COLLECTING_TICKET_TIME",   # off-peak/anytime
    "COLLECTING_TICKET_AGE": "COLLECTING_TICKET_AGE",     # adult/child
    "PROVIDING_PREDICTION": "PROVIDING_PREDICTION",
    "PROVIDING_TICKET_INFO": "PROVIDING_TICKET_INFO",
    "FOLLOW_UP": "FOLLOW_UP",
    "GOODBYE": "GOODBYE",
    "ASK_SPECIAL_TICKET": "ASK_SPECIAL_TICKET",
    "COLLECTING_SPECIAL_TICKET": "COLLECTING_SPECIAL_TICKET",
}

# Create a new conversation session
def create_conversation_session():
    session_id = str(uuid.uuid4())
    active_conversations[session_id] = {
        "state": CONVERSATION_STATES["GREETING"],
        "journey_info": {},
        "last_interaction": time.time(),
        "missing_fields": [],
        "last_message": None
    }
    return session_id

# Update an existing conversation
def update_conversation(session_id, user_input):
    if session_id not in active_conversations:
        session_id = create_conversation_session()
    
    conversation = active_conversations[session_id]
    conversation["last_interaction"] = time.time()
    
    # Save user input to conversation history
    if "history" not in conversation:
        conversation["history"] = []
    
    conversation["history"].append({"role": "user", "message": user_input})
    return conversation

# Save bot response to conversation history
def save_bot_response(session_id, response):
    if session_id in active_conversations:
        conversation = active_conversations[session_id]
        if "history" not in conversation:
            conversation["history"] = []
        
        conversation["history"].append({"role": "bot", "message": response})
        conversation["last_message"] = response

# function to match user input to intent:
def match_intent(user_input):
    user_input = user_input.lower()
    for intent in intents["intents"]:
        for pattern in intent["patterns"]:
            if pattern in user_input:
                return intent["tag"]

    # Enhanced detection for booking
    if any(word in user_input for word in ["book", "buy", "purchase", "reserve", "get ticket"]):
        return "book_ticket"

    # Enhanced detection for ticket price queries
    if any(word in user_input for word in ["ticket", "price", "cost", "fare", "how much", "cheap"]):
        return "ticket_price"
    
    # Enhanced detection for delay queries
    if any(word in user_input for word in ["delay", "train", "late", "on time", "journey", "travel", "from", "to"]):
        return "delay_prediction"

    return "unknown"

# function to extract train journey details using NLP:
def extract_train_info(text, existing_info=None):
    """Extract train journey details using JourneyExtractor."""
    # Start with existing info if provided
    result = existing_info or {}
    
    # Extract new information
    journey_info = journey_extractor.extract_journey_details(text)
    
    # Update with new info, only if not already present
    for key in ["origin", "destination", "departure_time", "departure_day"]:
        if key in journey_info and journey_info[key] and (key not in result or not result[key]):
            result[key] = journey_info[key]
    
    text_lower = text.lower()
    # Ticket type
    if "single" in text_lower or "one way" in text_lower:
        result["ticket_type"] = "SINGLE"
    elif "return" in text_lower or "round trip" in text_lower:
        result["ticket_type"] = "RETURN"
    # Ticket time
    if "off-peak" in text_lower or "off peak" in text_lower:
        result["ticket_time"] = "OFF-PEAK"
    elif "anytime" in text_lower or "any time" in text_lower:
        result["ticket_time"] = "ANYTIME"
    # Ticket age
    if "adult" in text_lower:
        result["ticket_age"] = "ADULT"
    elif "child" in text_lower or "kid" in text_lower:
        result["ticket_age"] = "CHILD"
    
    return result if result else None

# Check what information is missing
def get_missing_fields(journey_info, task=None):
    if task == "ticket_price":
        required_fields = [
            "origin", "destination", "departure_day", "departure_time",
            "ticket_type", "ticket_time", "ticket_age"
        ]
    else:
        required_fields = ["origin", "destination", "departure_time", "departure_day"]
    missing = []
    for field in required_fields:
        if field not in journey_info or not journey_info[field]:
            missing.append(field)
    return missing

# --- Helper for ticket price fields ---
def get_missing_ticket_fields(journey_info):
    required_fields = [
        "origin", "destination", "departure_day", "departure_time",
        "ticket_type", "ticket_time", "ticket_age"
    ]
    return [field for field in required_fields if not journey_info.get(field)]

# --- Helper for delay prediction fields ---
def get_missing_delay_fields(journey_info):
    required_fields = ["origin", "destination", "departure_time", "departure_day"]
    return [field for field in required_fields if not journey_info.get(field)]

# Updated question generator for ticket fields
def generate_collecting_question(missing_field, journey_info):
    if missing_field == "origin":
        return "Where will you be departing from?"
    
    elif missing_field == "destination":
        origin = journey_info.get("origin", "your location")
        return f"Where are you traveling to from {origin}?"
    
    elif missing_field == "departure_time":
        origin = journey_info.get("origin", "your origin")
        destination = journey_info.get("destination", "your destination")
        return f"What time do you plan to travel from {origin} to {destination}?"
    
    elif missing_field == "departure_day":
        return "Which day will you be traveling?"
    
    # New questions for ticket fields
    elif missing_field == "ticket_type":
        return "Is this a single or return ticket?"
    
    elif missing_field == "ticket_time":
        return "Would you like an off-peak or anytime ticket?"
    
    elif missing_field == "ticket_age":
        return "Is this ticket for an adult or a child?"
    
    return "Could you provide more details about your journey?"

# Updated handle_direct_answer function
def handle_direct_answer(user_input, conversation):
    state = conversation["state"]
    user_input_original = user_input.strip()
    user_input_upper = user_input_original.upper()
    user_input_lower = user_input_original.lower()

    if not conversation.get("journey_info"):
        conversation["journey_info"] = {}

    # Helper: Find all station names that contain the user's input
    def find_station_options(query):
        return [(name, STATION_NAME_TO_CODE[name]) for name in STATION_NAME_TO_CODE if query in name]

    # Handle origin
    if state == CONVERSATION_STATES["COLLECTING_ORIGIN"]:
        if user_input_upper in STATION_CODES:
            conversation["journey_info"]["origin"] = user_input_upper
            return True
        elif user_input_lower in STATION_NAME_TO_CODE:
            conversation["journey_info"]["origin"] = STATION_NAME_TO_CODE[user_input_lower]
            return True
        else:
            # Try to find partial matches
            matches = find_station_options(user_input_lower)
            if matches:
                options = "\n".join(f"- {name.title()} ({code})" for name, code in matches)
                conversation["last_message"] = (
                    f"Please be more specific. Did you mean one of these stations?\n{options}\n"
                    "Please type the full station name or code."
                )
                return False   # <-- ADD THIS LINE
            else:
                conversation["last_message"] = (
                    "Please enter a valid station code or station name for your departure (e.g., LST or London Liverpool Street)."
                )
                return False

    # Handle destination
    elif state == CONVERSATION_STATES["COLLECTING_DESTINATION"]:
        if user_input_upper in STATION_CODES:
            conversation["journey_info"]["destination"] = user_input_upper
            return True
        elif user_input_lower in STATION_NAME_TO_CODE:
            conversation["journey_info"]["destination"] = STATION_NAME_TO_CODE[user_input_lower]
            return True
        else:
            # Try to find partial matches
            matches = find_station_options(user_input_lower)
            if matches:
                options = "\n".join(f"- {name.title()} ({code})" for name, code in matches)
                conversation["last_message"] = (
                    f"Please be more specific. Did you mean one of these stations?\n{options}\n"
                    "Please type the full station name or code."
                )
                return False   # <-- ADD THIS LINE
            else:
                conversation["last_message"] = (
                    "Please enter a valid station code or station name for your destination (e.g., NRW or Norwich)."
                )
            return False
        
    elif state == CONVERSATION_STATES["COLLECTING_TIME"]:
        conversation["journey_info"]["departure_time"] = user_input
        return True
        
    elif state == CONVERSATION_STATES["COLLECTING_DAY"]:
        conversation["journey_info"]["departure_day"] = user_input
        return True
    
    # Handle new ticket-specific states
    elif state == CONVERSATION_STATES["COLLECTING_TICKET_TYPE"]:
        if "single" in user_input_original.lower():
            conversation["journey_info"]["ticket_type"] = "SINGLE"
        else:
            conversation["journey_info"]["ticket_type"] = "RETURN"
        return True
        
    elif state == CONVERSATION_STATES["COLLECTING_TICKET_TIME"]:
        if "off" in user_input_original.lower():
            conversation["journey_info"]["ticket_time"] = "OFF-PEAK"
        else:
            conversation["journey_info"]["ticket_time"] = "ANYTIME"
        return True
        
    elif state == CONVERSATION_STATES["COLLECTING_TICKET_AGE"]:
        if "adult" in user_input_original.lower():
            conversation["journey_info"]["ticket_age"] = "ADULT"
        else:
            conversation["journey_info"]["ticket_age"] = "CHILD"
        return True
        
    return False

# --- Add a simple ticket price formatter ---
def format_ticket_price(journey_info):
    # This is a mock, replace with real pricing logic or API as needed
    base = 20.0
    if journey_info.get("ticket_type") == "RETURN":
        base *= 1.7
    if journey_info.get("ticket_time") == "OFF-PEAK":
        base *= 0.7
    if journey_info.get("ticket_age") == "CHILD":
        base *= 0.5
    price = round(base, 2)
    return (f"For a {journey_info.get('ticket_age','ADULT').lower()} "
            f"{journey_info.get('ticket_time','ANYTIME').lower()} "
            f"{journey_info.get('ticket_type','SINGLE').lower()} ticket from "
            f"{journey_info.get('origin','?')} to {journey_info.get('destination','?')}, "
            f"the price is £{price:.2f}.\nYou can purchase this ticket at the station or online.")

SPECIAL_TICKET_KEYS = {
    "flexi season": "Flexi Season",
    "travelcard": "TRAVELCARD 7DS",
    "off-peak day travelcard": "OFF-PEAK TCDSTD",
    "carnet": "CARNET SINGLE",
    "child flatfare": "CHILD FLTFARE R",
    "season ticket": "SEASON STD",           # Add this line
    "season std": "SEASON STD"               # Allow direct match as well
}
SPECIAL_TICKET_NAMES = list(SPECIAL_TICKET_KEYS.keys())

# function to generate chatbot response with improved conversation capabilities
def generate_response(user_input, session_id=None):
    if not session_id:
        session_id = create_conversation_session()
    conversation = update_conversation(session_id, user_input)
    intent_tag = match_intent(user_input)
    direct_answer_handled = handle_direct_answer(user_input, conversation)

    # --- Handle special ticket prompt state ---
    if conversation["state"] == CONVERSATION_STATES["ASK_SPECIAL_TICKET"]:
        if user_input.strip().lower() in ["yes", "y"]:
            conversation["state"] = CONVERSATION_STATES["COLLECTING_SPECIAL_TICKET"]
            prompt = (
                "Which special ticket do you need? (Flexi Season, Travelcard, Carnet Single, "
                "Off-Peak Day Travelcard, Child Flatfare, Season Ticket)"
            )
            save_bot_response(session_id, prompt)
            return prompt, session_id
        elif user_input.strip().lower() in ["no", "n"]:
            conversation["journey_info"]["special_ticket"] = None
            conversation["state"] = CONVERSATION_STATES["PROVIDING_TICKET_INFO"]
            # Continue to price selection below (let the rest of the function run)
        else:
            prompt = "Please answer 'yes' or 'no'. Do you need a special ticket type?"
            save_bot_response(session_id, prompt)
            return prompt, session_id

    if conversation["state"] == CONVERSATION_STATES["COLLECTING_SPECIAL_TICKET"]:
        normalized = None
        for name in SPECIAL_TICKET_NAMES:
            if name in user_input.lower():
                normalized = name
                break
        if normalized:
            conversation["journey_info"]["special_ticket"] = normalized
            conversation["state"] = CONVERSATION_STATES["PROVIDING_TICKET_INFO"]
            # Continue to price selection below (let the rest of the function run)
        else:
            prompt = (
                "Sorry, I didn't recognize that special ticket. Please choose from: "
                "Flexi Season, Travelcard, Carnet Single, Off-Peak Day Travelcard, Child Flatfare, Season Ticket."
            )
            save_bot_response(session_id, prompt)
            return prompt, session_id

    # --- Handle FOLLOW_UP state ---
    if conversation["state"] == CONVERSATION_STATES["FOLLOW_UP"]:
        if user_input.strip().lower() in ["no", "no thanks", "nothing", "that's all", "exit", "bye", "goodbye"]:
            # Reset state and info
            conversation["state"] = CONVERSATION_STATES["GREETING"]
            conversation["current_task"] = None
            conversation["journey_info"] = {}
            # Choose a greeting
            greeting = random.choice([
                "Hello! I'm RailBot, your railway assistant. How can I help you today?",
                "Hi there! Need information about train journeys or delays?",
                "Welcome! I can help you with train information and delay predictions. What would you like to know?"
            ])
            save_bot_response(session_id, greeting)
            return greeting, session_id
        # If user says yes or asks a new question, reset and continue
        elif user_input.strip().lower() in ["yes", "sure", "okay", "yep"]:
            response = "Great! What would you like to do next? You can ask for ticket prices or delay predictions."
            conversation["state"] = CONVERSATION_STATES["GREETING"]
            conversation["current_task"] = None
            conversation["journey_info"] = {}
            save_bot_response(session_id, response)
            return response, session_id
        # If user asks for delay prediction after ticket, use last journey_info
        elif "delay" in user_input.lower():
            # Use previous journey_info for delay prediction
            delay = predict_delay_from_input("", weather=None, journey_info=conversation["journey_info"])
            response = f"Here's the delay prediction for your journey:\n\n{delay}\n\nAnything else I can help with?"
            save_bot_response(session_id, response)
            return response, session_id
        # Otherwise, treat as a new query (reset and continue)
        else:
            conversation["state"] = CONVERSATION_STATES["GREETING"]
            conversation["current_task"] = None
            # Do not clear journey_info so user can use previous info for delay
            # Continue to intent matching as normal

    # Check for conversation-ending intents first
    if intent_tag == "goodbye":
        conversation["state"] = CONVERSATION_STATES["GOODBYE"]
        response = random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "goodbye"][0])
        save_bot_response(session_id, response)
        return response, session_id
    
    # Handle different states and intents
    if intent_tag == "greeting":
        conversation["state"] = CONVERSATION_STATES["GREETING"]
        response = random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "greeting"][0])
        save_bot_response(session_id, response)
        return response, session_id
    
    elif intent_tag == "thanks":
        response = random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "thanks"][0])
        save_bot_response(session_id, response)
        return response, session_id
    
    elif intent_tag == "name":
        response = random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "name"][0])
        save_bot_response(session_id, response)
        return response, session_id
    
    elif intent_tag == "help":
        response = random.choice([i["responses"] for i in intents["intents"] if i["tag"] == "help"][0])
        save_bot_response(session_id, response)
        return response, session_id
    
    elif intent_tag == "book_ticket":
        booking_url = f"https://brfares.com"
        response = (
        f"Great! You can book your ticket directly at this link:\n{booking_url}\n"
        "Click the link to continue your booking."
        )
        save_bot_response(session_id, response)
        return response, session_id
    
    # --- Ticket price intent ---
    if (
        intent_tag == "ticket_price"
        or conversation.get("current_task") == "ticket_price"
    ):
        conversation["current_task"] = "ticket_price"
        if not direct_answer_handled:
            journey_info = extract_train_info(user_input, conversation.get("journey_info", {}))
            if journey_info:
                conversation["journey_info"] = journey_info
        missing_fields = get_missing_ticket_fields(conversation.get("journey_info", {}))
        conversation["missing_fields"] = missing_fields
        if not missing_fields:
            if "special_ticket" not in conversation["journey_info"]:
                conversation["state"] = CONVERSATION_STATES["ASK_SPECIAL_TICKET"]
                prompt = (
                    "Do you need a special ticket type such as Flexi Season, Travelcard, Carnet Single, "
                    "Off-Peak Day Travelcard, Child Flatfare, or Season Ticket? (yes/no)"
                )
                save_bot_response(session_id, prompt)
                return prompt, session_id
            conversation["state"] = CONVERSATION_STATES["PROVIDING_TICKET_INFO"]
            # Fetch real fares
            origin = conversation["journey_info"]["origin"]
            destination = conversation["journey_info"]["destination"]
            fares_json = fetch_real_fare(origin, destination)
            if fares_json:
                ticket_name, price = select_ticket_price(fares_json, conversation["journey_info"])
                if ticket_name == "NO_SINGLE":
                    # No single ticket available, ask about return
                    conversation["journey_info"]["ticket_type"] = "RETURN"
                    conversation["state"] = "ASK_RETURN_IF_NO_SINGLE"
                    prompt = "There are no off-peak single tickets available for this journey. Would you like a return ticket instead? (yes/no)"
                    save_bot_response(session_id, prompt)
                    return prompt, session_id
                elif ticket_name == "NO_RETURN":
                    # No return ticket available, restart
                    conversation["state"] = CONVERSATION_STATES["GREETING"]
                    conversation["current_task"] = None
                    conversation["journey_info"] = {}
                    prompt = "There are no return tickets available for this journey. Let's start again. Where will you be departing from?"
                    save_bot_response(session_id, prompt)
                    return prompt, session_id
                elif ticket_name and price:
                    # Normal flow
                    booking_url = f"https://www.brfares.com/#!fares?orig={origin}&dest={destination}"
                    ticket_info = (
                        f"For a {conversation['journey_info'].get('ticket_age','ADULT').lower()} "
                        f"{conversation['journey_info'].get('ticket_time','ANYTIME').lower()} "
                        f"{conversation['journey_info'].get('ticket_type','SINGLE').lower()} ticket "
                        f"({ticket_name}) from {origin} to {destination}, the price is {price}.\n"
                        f"You can book this ticket here: {booking_url}"
                    )
                else:
                    ticket_info = "Sorry, I couldn't find a matching ticket for your request."
            else:
                ticket_info = "Sorry, I couldn't fetch fare information at this time."

            random_followup = random.choice([
                "Would you like to check for delays on this route?",
                "Is there anything else you'd like to know about this journey?",
                "Can I help you with anything else today?",
            ])
            conversation["state"] = CONVERSATION_STATES["FOLLOW_UP"]
            full_response = f"{ticket_info}\n\n{random_followup}"
            save_bot_response(session_id, full_response)
            return full_response, session_id
        else:
            missing_field = missing_fields[0]
            if missing_field == "origin":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_ORIGIN"]
            elif missing_field == "destination":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_DESTINATION"]
            elif missing_field == "departure_time":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_TIME"]
            elif missing_field == "departure_day":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_DAY"]
            elif missing_field == "ticket_type":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_TICKET_TYPE"]
            elif missing_field == "ticket_time":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_TICKET_TIME"]
            elif missing_field == "ticket_age":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_TICKET_AGE"]
            question = generate_collecting_question(missing_field, conversation["journey_info"])
            save_bot_response(session_id, question)
            return question, session_id

    # --- Delay prediction intent ---
    if (
        intent_tag == "delay_prediction"
        or conversation.get("current_task") == "delay_prediction"
    ):
        conversation["current_task"] = "delay_prediction"
        if not direct_answer_handled:
            journey_info = extract_train_info(user_input, conversation.get("journey_info", {}))
            if journey_info:
                conversation["journey_info"] = journey_info
            else:
                conversation["journey_info"] = conversation.get("journey_info", {})
        missing_fields = get_missing_delay_fields(conversation.get("journey_info", {}))
        conversation["missing_fields"] = missing_fields
        if not missing_fields:
            conversation["state"] = CONVERSATION_STATES["PROVIDING_PREDICTION"]
            train_info = conversation["journey_info"]
            understood_msg = f"I understand you want train information for a journey from {train_info['origin']} to {train_info['destination']}"
            if "departure_time" in train_info:
                understood_msg += f" at {train_info['departure_time']}"
            if "departure_day" in train_info:
                understood_msg += f" on {train_info['departure_day']}"
            weather = get_random_weather()
            delay = predict_delay_from_input(user_input, weather)
            crowd_msg = get_train_crowd_info(user_input, weather)
            full_response = f"{understood_msg}.\n\n{delay}"
            if crowd_msg:
                full_response += f"\n\n{crowd_msg}"
            random_followup = random.choice([
                "Is there anything else you'd like to know about this journey?",
                "Would you like to check another train journey?",
                "Can I help you with anything else today?",
            ])
            conversation["state"] = CONVERSATION_STATES["FOLLOW_UP"]
            full_response += f"\n\n{random_followup}"
            save_bot_response(session_id, full_response)
            return full_response, session_id
        else:
            missing_field = missing_fields[0]
            if missing_field == "origin":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_ORIGIN"]
            elif missing_field == "destination":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_DESTINATION"]
            elif missing_field == "departure_time":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_TIME"]
            elif missing_field == "departure_day":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_DAY"]
            question = generate_collecting_question(missing_field, conversation["journey_info"])
            save_bot_response(session_id, question)
            return question, session_id

    # --- Unknown intent fallback ---
    response = ("I can help you with train delay predictions and ticket prices. You can ask me things like:\n\n"
                "• Predict delay from Birmingham to London at 15:30 on Friday\n"
                "• How much is an off-peak return ticket from Norwich to London?\n"
                "• Will my train from Manchester to Liverpool be delayed tomorrow morning?")
    save_bot_response(session_id, response)
    return response, session_id

def fetch_real_fare(origin, destination):
    url = f"http://localhost:3000/?originStation={origin}&destinationStation={destination}"
    try:
        resp = requests.get(url, timeout=15)
        print(f"Fetching fares from: {url}")
        print(f"Status code: {resp.status_code}")
        print(f"Response text: {resp.text}")
        if resp.status_code == 200:
            return resp.json()
        else:
            return None
    except Exception as e:
        print(f"Error fetching fares: {e}")
        return None

def select_ticket_price(fares_json, journey_info):
    ticket_age = journey_info.get("ticket_age", "ADULT").capitalize()
    special_ticket = journey_info.get("special_ticket")

    # If user requested a special ticket, only show that
    if special_ticket:
        key = SPECIAL_TICKET_KEYS.get(special_ticket.lower())
        if key and key in fares_json:
            ticket = fares_json[key]
            price = ticket.get(ticket_age)
            if price:
                return key, price
        return None, None

    # Otherwise, exclude special tickets from candidates
    exclude_keys = set(SPECIAL_TICKET_KEYS.values())
    ticket_type = journey_info.get("ticket_type", "").upper()
    ticket_time = journey_info.get("ticket_time", "").upper()

    # Try to find the requested ticket
    if ticket_type == "SINGLE":
        candidate = "OFF-PEAK S" if ticket_time == "OFF-PEAK" else "ANYTIME S"
        for key in fares_json:
            if candidate in key.upper() and key not in exclude_keys:
                ticket = fares_json[key]
                price = ticket.get(ticket_age)
                if price:
                    return key, price
        # If not found, return special marker
        return "NO_SINGLE", None

    elif ticket_type == "RETURN":
        candidate = "OFF-PEAK R" if ticket_time == "OFF-PEAK" else "ANYTIME R"
        for key in fares_json:
            if candidate in key.upper() and key not in exclude_keys:
                ticket = fares_json[key]
                price = ticket.get(ticket_age)
                if price:
                    return key, price
        return "NO_RETURN", None

    # Fallback: any non-special ticket
    for key, ticket in fares_json.items():
        if key not in exclude_keys:
            price = ticket.get(ticket_age)
            if price:
                return key, price
    return None, None

# Run chatbot with improved conversation flow
if __name__ == "__main__":
    print("RailBot - your railway assistant (type 'exit' to stop)")
    session_id = create_conversation_session()
    
    # Start with a greeting
    greeting = random.choice([
        "Hello! I'm RailBot, your railway assistant. How can I help you today?",
        "Hi there! Need information about train journeys or delays?",
        "Welcome! I can help you with train information and delay predictions. What would you like to know?"
    ])
    print(f"Bot: {greeting}")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
            closing = random.choice([
                "Goodbye! Have a safe journey!",
                "Thanks for chatting. Have a great day!",
                "See you next time! Safe travels!"
            ])
            print(f"Bot: {closing}")
            break
            
        response, session_id = generate_response(user_input, session_id)
        # Get the conversation object
        conversation = active_conversations[session_id]
        if conversation.get("last_message"):
            print(f"Bot: {conversation['last_message']}")
        else:
            print(f"Bot: {response}")


