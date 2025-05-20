# imports:
import random
import re
import uuid
import time
import warnings
from train_chatbot import predict_delay_from_input
from extra_features import get_train_crowd_info, get_random_weather
from nlpprocessor import JourneyExtractor  # Import JourneyExtractor for NLP

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
            "tag": "help",
            "patterns": ["help", "what can you do", "how does this work", "features", "commands"],
            "responses": ["I can help you with:\n• Train delay predictions\n• Journey information\n\nJust ask me questions like 'Will my train from London to Manchester be delayed?' or 'Predict delay from Birmingham to Oxford tomorrow afternoon'"]
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
    "PROVIDING_PREDICTION": "PROVIDING_PREDICTION",
    "FOLLOW_UP": "FOLLOW_UP",
    "GOODBYE": "GOODBYE"
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
    
    # Don't add defaults here - let the conversation flow handle this
    return result if result else None

# Check what information is missing
def get_missing_fields(journey_info):
    missing = []
    required_fields = ["origin", "destination", "departure_time", "departure_day"]
    
    for field in required_fields:
        if field not in journey_info or not journey_info[field]:
            missing.append(field)
    
    return missing

# Generate questions to collect missing information
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
    
    return "Could you provide more details about your journey?"

# Add this function to handle direct answers
def handle_direct_answer(user_input, conversation):
    """Handle direct answers to specific questions based on conversation state."""
    state = conversation["state"]
    user_input = user_input.strip().upper()
    
    # If we're collecting specific information and get a single-word answer
    if state == CONVERSATION_STATES["COLLECTING_ORIGIN"]:
        if not conversation.get("journey_info"):
            conversation["journey_info"] = {}
        conversation["journey_info"]["origin"] = user_input
        return True
        
    elif state == CONVERSATION_STATES["COLLECTING_DESTINATION"]:
        if not conversation.get("journey_info"):
            conversation["journey_info"] = {}
        conversation["journey_info"]["destination"] = user_input
        return True
        
    elif state == CONVERSATION_STATES["COLLECTING_TIME"]:
        if not conversation.get("journey_info"):
            conversation["journey_info"] = {}
        conversation["journey_info"]["departure_time"] = user_input
        return True
        
    elif state == CONVERSATION_STATES["COLLECTING_DAY"]:
        if not conversation.get("journey_info"):
            conversation["journey_info"] = {}
        conversation["journey_info"]["departure_day"] = user_input
        return True
        
    return False

# function to generate chatbot response with improved conversation capabilities
def generate_response(user_input, session_id=None):
    # Create or update conversation session
    if not session_id:
        session_id = create_conversation_session()
    
    conversation = update_conversation(session_id, user_input)
    intent_tag = match_intent(user_input)
    
    # First check for special cases - direct answers to questions
    direct_answer_handled = handle_direct_answer(user_input, conversation)
    
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
    
    elif intent_tag == "delay_prediction" or conversation["state"] in [CONVERSATION_STATES["COLLECTING_ORIGIN"], 
                                                                     CONVERSATION_STATES["COLLECTING_DESTINATION"],
                                                                     CONVERSATION_STATES["COLLECTING_TIME"],
                                                                     CONVERSATION_STATES["COLLECTING_DAY"]]:
        # Extract journey details, starting with any we've already collected
        if not direct_answer_handled:
            journey_info = extract_train_info(user_input, conversation.get("journey_info", {}))
            if journey_info:
                conversation["journey_info"] = journey_info
            else:
                conversation["journey_info"] = conversation.get("journey_info", {})
        
        # Check what information is still missing - don't let defaults bypass this!
        missing_fields = get_missing_fields(conversation.get("journey_info", {}))
        conversation["missing_fields"] = missing_fields
        
        # If we have all required information
        if not missing_fields:
            conversation["state"] = CONVERSATION_STATES["PROVIDING_PREDICTION"]
            train_info = conversation["journey_info"]
            
            # Create a friendly format message showing what we understood
            understood_msg = f"I understand you want train information for a journey from {train_info['origin']} to {train_info['destination']}"
            
            if "departure_time" in train_info:
                understood_msg += f" at {train_info['departure_time']}"
            
            if "departure_day" in train_info:
                understood_msg += f" on {train_info['departure_day']}"
            
            # Get the delay prediction and weather information
            weather = get_random_weather()
            delay = predict_delay_from_input(user_input, weather)
            crowd_msg = get_train_crowd_info(user_input, weather)
            
            # Return complete response
            full_response = f"{understood_msg}.\n\n{delay}"
            if crowd_msg:
                full_response += f"\n\n{crowd_msg}"
                
            # Add follow-up prompt
            random_followup = random.choice([
                "Is there anything else you'd like to know about this journey?",
                "Would you like to check another train journey?",
                "Can I help you with anything else today?",
            ])
            
            conversation["state"] = CONVERSATION_STATES["FOLLOW_UP"]
            full_response += f"\n\n{random_followup}"
            
            save_bot_response(session_id, full_response)
            return full_response, session_id
            
        # If we're missing information, ask for it
        else:
            # Get the first missing field and set state accordingly
            missing_field = missing_fields[0]
            
            if missing_field == "origin":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_ORIGIN"]
            elif missing_field == "destination":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_DESTINATION"]
            elif missing_field == "departure_time":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_TIME"]
            elif missing_field == "departure_day":
                conversation["state"] = CONVERSATION_STATES["COLLECTING_DAY"]
                
            # Ask a question to collect the missing information
            question = generate_collecting_question(missing_field, conversation["journey_info"])
            save_bot_response(session_id, question)
            return question, session_id
    
    # Handle unknown intent or state
    else:
        response = ("I'm here to help with train delay predictions. You can ask me things like:\n\n"
                    "• Predict delay from Birmingham to London at 15:30 on Friday\n"
                    "• Will my train from Manchester to Liverpool be delayed tomorrow morning?\n"
                    "• Check delays from Cambridge to Oxford at 9am")
        save_bot_response(session_id, response)
        return response, session_id

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
        print(f"Bot: {response}")
