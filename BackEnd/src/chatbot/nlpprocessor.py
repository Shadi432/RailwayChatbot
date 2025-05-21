import re
from datetime import datetime
import os
from thefuzz import process, fuzz
import pytz

class JourneyExtractor:
    def __init__(self, debug=False):
        """Initialize the journey extractor with station data."""
        self.debug = debug
        self.uk_timezone = pytz.timezone('Europe/London')
        self.today = datetime.now(self.uk_timezone)
        
        # Common UK station names and codes
        self.station_mapping = {
            "birmingham": "BHM",
            "london": "LST",
            "euston": "EUS",
            "manchester": "MAN",
            "liverpool": "LIV",
            "edinburgh": "EDB",
            "glasgow": "GLC",
            "norwich": "NRW",
            "cambridge": "CBG",
            "oxford": "OXF",
            "york": "YRK",
            "newcastle": "NCL",
            "leeds": "LDS",
            "bristol": "BRI",
            "cardiff": "CDF",
            "stratford": "SRA",
            "watford": "WAT",
            "brighton": "BTN"
        }
        
        # Load station codes from dataFile.txt
        data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../dataFile.txt"))
        try:
            with open(data_path, 'r') as file:
                for line in file:
                    parts = line.strip().split(',')
                    if len(parts) > 1:
                        # Add station codes to our mapping
                        self.station_mapping[parts[0].lower()] = parts[0]
                        self.station_mapping[parts[1].lower()] = parts[1]
        except:
            # File loading failed, continue with default mapping
            pass

        # Now build station_data
        self.station_data = list(self.station_mapping.values())

        # Special time mappings
        self.time_keywords = {
            "morning": "09:00",
            "afternoon": "14:00",
            "evening": "18:00",
            "night": "21:00"
        }
        
        # Day names mapping
        self.day_mapping = {
            "monday": "Monday", "mon": "Monday",
            "tuesday": "Tuesday", "tue": "Tuesday", "tues": "Tuesday",
            "wednesday": "Wednesday", "wed": "Wednesday",
            "thursday": "Thursday", "thu": "Thursday", "thur": "Thursday",
            "friday": "Friday", "fri": "Friday",
            "saturday": "Saturday", "sat": "Saturday", 
            "sunday": "Sunday", "sun": "Sunday",
            "today": self.today.strftime("%A"),
            "tomorrow": self._get_tomorrow(),
            "weekend": "Saturday"  # Default to Saturday for "weekend"
        }
    
    def _get_tomorrow(self):
        """Get tomorrow's day name."""
        tomorrow_idx = (self.today.weekday() + 1) % 7
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days[tomorrow_idx]
    
    def _log(self, message):
        """Conditionally print debug messages."""
        if self.debug:
            print(f"Debug: {message}")
    
    def match_station(self, station_text):
        """Match station name using improved fuzzy matching."""
        if not station_text:
            return None
            
        # Clean input
        station_text = station_text.strip().upper()
        
        # Common mappings for major stations
        station_mappings = {
            "LONDON": "LST",
            "OXFORD": "OXF",
            "CAMBRIDGE": "CBG", 
            "BIRMINGHAM": "BHM",
            "MANCHESTER": "MAN",
            "LIVERPOOL": "LIV",
            "NORWICH": "NRW",
            "EDINBURGH": "EDB"
        }
        
        # Check direct mapping first
        if station_text in station_mappings:
            return station_mappings[station_text]
            
        # Check for exact match in station data
        if station_text in self.station_data:
            return station_text
            
        # Try fuzzy matching with LOWER threshold (65 instead of 75/80)
        matches = process.extract(station_text, self.station_data, limit=3)
        for match, score in matches:
            if score >= 65:  # Lower threshold for better matching
                self._log(f"Fuzzy matched '{station_text}' to '{match}' with score {score}")
                return match
                
        # If all else fails, return the input to allow flow to continue
        return station_text
    
    def parse_time(self, time_text):
        """Parse time from various formats."""
        if not time_text:
            return None
            
        time_text = time_text.strip().lower()
        
        # Check for time keywords
        if time_text in self.time_keywords:
            return self.time_keywords[time_text]
            
        # Handle "5" -> "05:00" and "5:30" -> "05:30"
        if time_text.isdigit():
            hour = int(time_text)
            if 0 <= hour <= 23:
                return f"{hour:02d}:00"
        
        # Handle HH:MM format
        time_match = re.match(r'(\d{1,2})(?::(\d{2}))?(?:\s*(am|pm))?', time_text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            period = time_match.group(3)
            
            if period == 'pm' and hour < 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
                
            return f"{hour:02d}:{minute:02d}"
            
        return None
    
    def parse_day(self, day_text):
        """Parse day from various formats."""
        if not day_text:
            return None
            
        day_text = day_text.strip().lower()
        
        # Check for day names in our mapping
        for key, value in self.day_mapping.items():
            if key in day_text:
                return value
                
        return None
    
    def extract_journey_details(self, text):
        """Extract journey details from user input."""
        text = text.lower().strip()
        result = {}
        
        # Main pattern that properly handles the components
        pattern = r'(?:.*?from\s+)([\w\s]+?)(?:\s+to\s+)([\w\s]+?)(?:(?:\s+at\s+)([\w\s:]+?))?(?:(?:\s+on\s+)([\w\s]+?))?(?:\s+|$)'
        
        # Alternative patterns
        alt_patterns = [
            # "Delay Birmingham to London tomorrow at 5"
            r'(?:.*?)(?:from\s+)?([\w\s]+?)(?:\s+to\s+)([\w\s]+?)(?:\s+(tomorrow|today))?(?:\s+at\s+([\w\s:]+))?(?:\s+|$)',
            
            # "Will my train from X to Y be late?"
            r'(?:.*?train\s+from\s+)([\w\s]+?)(?:\s+to\s+)([\w\s]+?)(?:\s+.*?)?(?:\s+|$)'
        ]
        
        # Try main pattern first
        match = re.search(pattern, text)
        if match:
            origin, destination, time_text, day_text = match.groups()
        else:
            # Try alternative patterns
            for alt_pattern in alt_patterns:
                match = re.search(alt_pattern, text)
                if match:
                    # Handle different group structures
                    groups = match.groups()
                    if len(groups) == 4:  # Pattern with tomorrow/today
                        origin, destination, day_text, time_text = groups
                    elif len(groups) == 2:  # Simple pattern
                        origin, destination = groups
                        time_text, day_text = None, None
                    break
            else:
                self._log("No pattern match found")
                return {}
        
        # Clean up extraction results
        if origin:
            origin = origin.strip()
            matched_origin = self.match_station(origin)
            if matched_origin:
                result["origin"] = matched_origin
                
        if destination:
            destination = destination.strip()
            matched_destination = self.match_station(destination)
            if matched_destination:
                result["destination"] = matched_destination
    
        if time_text:
            time_value = self.parse_time(time_text)
            if time_value:
                result["departure_time"] = time_value
            
        if day_text:
            day_value = self.parse_day(day_text)
            if day_value:
                result["departure_day"] = day_value
    
        self._log(f"Extracted journey details: {result}")
        return result


extractor = JourneyExtractor(debug=False)

# Updated extract_train_info function to extract ticket details
def extract_train_info(text, existing_info=None):
    """Extract train journey and ticket details using JourneyExtractor."""
    # Start with existing info if provided
    result = existing_info or {}
    
    # Extract new information
    journey_info = extractor.extract_journey_details(text)
    
    # Basic journey info
    for key in ["origin", "destination", "departure_time", "departure_day"]:
        if key in journey_info and journey_info[key] and (key not in result or not result[key]):
            result[key] = journey_info[key]
    
    # Extract ticket_time (off-peak or anytime)
    text_lower = text.lower()
    if "off-peak" in text_lower or "off peak" in text_lower:
        result["ticket_time"] = "OFF-PEAK"
    elif "anytime" in text_lower or "any time" in text_lower:
        result["ticket_time"] = "ANYTIME"
        
    # Extract ticket_type (single or return)
    if "single" in text_lower or "one way" in text_lower:
        result["ticket_type"] = "SINGLE"
    elif "return" in text_lower or "round trip" in text_lower:
        result["ticket_type"] = "RETURN"
        
    # Extract ticket_age (adult or child)
    if "adult" in text_lower:
        result["ticket_age"] = "ADULT"
    elif "child" in text_lower or "kid" in text_lower:
        result["ticket_age"] = "CHILD"
    
    return result if result else None

# Function to get missing ticket fields
def get_missing_ticket_fields(journey_info):
    missing = []
    
    # Required fields for ticket price queries
    required_fields = [
        "origin", "destination", "ticket_time", "ticket_type", "ticket_age"
    ]
    
    for field in required_fields:
        if field not in journey_info or not journey_info[field]:
            missing.append(field)
    
    return missing

# Update existing get_missing_fields to check for task type
def get_missing_fields(journey_info, task="delay_prediction"):
    if task == "ticket_price":
        return get_missing_ticket_fields(journey_info)
    
    # Original function for delay prediction
    missing = []
    required_fields = ["origin", "destination", "departure_time", "departure_day"]
    
    for field in required_fields:
        if field not in journey_info or not journey_info[field]:
            missing.append(field)
    
    return missing

SPECIAL_TICKET_KEYS = {
    "flexi season": "Flexi Season",
    "travelcard": "TRAVELCARD 7DS",
    "off-peak day travelcard": "OFF-PEAK TCDSTD",
    "carnet": "CARNET SINGLE",
    "child flatfare": "CHILD FLTFARE R"
}
SPECIAL_TICKET_NAMES = list(SPECIAL_TICKET_KEYS.keys())

def normalize_special_ticket(user_input):
    user_input = user_input.lower()
    for name in SPECIAL_TICKET_NAMES:
        if name in user_input:
            return name
    return None