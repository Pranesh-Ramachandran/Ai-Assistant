"""
Maps Assistant - Conversational bilingual location assistance
Natural, helpful, privacy-respecting location queries
"""

import re
from typing import Optional, List
from location_resolver import location_resolver, Place
from gps_manager import gps_manager
import webbrowser

class MapsAssistant:
    def __init__(self):
        self.current_language = 'english'
        self.confidence_threshold = 0.3
        
        # Common place categories for "nearest" queries
        self.categories = {
            'hospital': ['hospital', 'மருத்துவமனை', 'clinic', 'medical'],
            'atm': ['atm', 'cash', 'bank machine', 'பணம்'],
            'restaurant': ['restaurant', 'hotel', 'food', 'உணவகம்', 'சாப்பாடு'],
            'petrol': ['petrol', 'fuel', 'gas station', 'பெட்ரோல்'],
            'school': ['school', 'பள்ளி'],
            'college': ['college', 'university', 'கல்லூரி'],
            'bank': ['bank', 'வங்கி'],
            'pharmacy': ['pharmacy', 'medical store', 'மருந்து கடை']
        }
    
    def set_language(self, language: str):
        """Set current conversation language"""
        self.current_language = language.lower()
    
    def handle_location_query(self, query: str) -> str:
        """Main handler for location-related queries"""
        query_lower = query.lower()
        
        # Check if internet is available
        if not self._check_internet():
            return self._get_offline_message()
        
        # Detect query type
        if any(word in query_lower for word in ['nearest', 'nearby', 'close', 'அருகில்', 'பக்கத்தில்']):
            return self._handle_nearby_query(query)
        elif any(word in query_lower for word in ['where is', 'where', 'எங்கே', 'எங்க']):
            return self._handle_where_query(query)
        elif any(word in query_lower for word in ['distance', 'how far', 'தூரம்', 'எவ்வளவு தூரம்']):
            return self._handle_distance_query(query)
        elif any(word in query_lower for word in ['directions', 'route', 'navigate', 'வழி', 'route']):
            return self._handle_directions_query(query)
        else:
            # General location search
            return self._handle_general_search(query)
    
    def _handle_nearby_query(self, query: str) -> str:
        """Handle 'nearest hospital' type queries"""
        # Extract category
        category = self._extract_category(query)
        if not category:
            return self._ask_clarification("What type of place are you looking for?")
        
        # Get current location
        location = gps_manager.get_current_location()
        if not location:
            return self._get_location_error()
        
        lat, lon = location
        
        # Search nearby places
        places = location_resolver.find_nearby(category, lat, lon)
        
        if not places:
            if self.current_language == 'tamil':
                return f"அருகில் {category} கிடைக்கவில்லை."
            else:
                return f"No {category} found nearby."
        
        # Return closest match
        closest = places[0]
        distance = location_resolver.calculate_distance(lat, lon, closest.latitude, closest.longitude)
        
        if self.current_language == 'tamil':
            response = f"அருகிலுள்ள {category} {closest.name} — {distance} கி.மீ தூரம்."
            if len(places) > 1:
                response += " இன்னும் சில விருப்பங்கள் காட்டவா?"
        else:
            response = f"The nearest {category} is {closest.name} — {distance} km away."
            if len(places) > 1:
                response += " Want me to list more options?"
        
        return response
    
    def _handle_where_query(self, query: str) -> str:
        """Handle 'where is Marina Beach' type queries"""
        # Extract place name
        place_name = self._extract_place_name(query)
        if not place_name:
            return self._ask_clarification("Which place are you asking about?")
        
        # Search for the place
        places = location_resolver.search_place(place_name)
        
        if not places:
            if self.current_language == 'tamil':
                return f"'{place_name}' என்ற இடம் கிடைக்கவில்லை. வேறு பெயரில் சொல்லி பார்க்கவும்."
            else:
                return f"I couldn't find '{place_name}'. Try a different name or add more details."
        
        # Check confidence and handle multiple results
        if len(places) == 1 or places[0].confidence > self.confidence_threshold:
            return self._format_place_response(places[0])
        else:
            return self._handle_multiple_matches(places, place_name)
    
    def _handle_distance_query(self, query: str) -> str:
        """Handle 'how far is Coimbatore' type queries"""
        place_name = self._extract_place_name(query)
        if not place_name:
            return self._ask_clarification("Distance to which place?")
        
        # Get current location
        location = gps_manager.get_current_location()
        if not location:
            return self._get_location_error()
        
        # Find the place
        places = location_resolver.search_place(place_name)
        if not places:
            if self.current_language == 'tamil':
                return f"'{place_name}' கிடைக்கவில்லை."
            else:
                return f"Couldn't find '{place_name}'."
        
        # Calculate distance
        target = places[0]
        lat, lon = location
        distance = location_resolver.calculate_distance(lat, lon, target.latitude, target.longitude)
        
        if self.current_language == 'tamil':
            return f"{target.name} இங்கிருந்து சுமார் {distance} கி.மீ தூரம்."
        else:
            return f"{target.name} is about {distance} km from here."
    
    def _handle_directions_query(self, query: str) -> str:
        place_name = self._extract_place_name(query)
        if not place_name:
            return self._ask_clarification("Directions to where?")
        places = location_resolver.search_place(place_name)
        if not places:
            return f"Couldn't find '{place_name}'."
        target = places[0]
        url = f"https://www.google.com/maps/dir/?api=1&destination={target.latitude},{target.longitude}"
        webbrowser.open(url)
        return f"Opening Google Maps directions to {target.name}."
    
    def _handle_general_search(self, query: str) -> str:
        """Handle general location searches"""
        places = location_resolver.search_place(query)
        
        if not places:
            if self.current_language == 'tamil':
                return "அந்த இடம் கிடைக்கவில்லை. மெதுவாக மறுபடி சொல்லுங்க."
            else:
                return "I'm not sure about that place. Say it once more — slowly."
        
        if len(places) == 1:
            return self._format_place_response(places[0])
        else:
            return self._handle_multiple_matches(places, query)
    
    def _extract_category(self, query: str) -> Optional[str]:
        """Extract place category from query"""
        query_lower = query.lower()
        
        for category, keywords in self.categories.items():
            if any(keyword in query_lower for keyword in keywords):
                return category
        
        return None
    
    def _extract_place_name(self, query: str) -> Optional[str]:
        """Extract place name from query"""
        # Remove common question words
        patterns = [
            r'where is (.+)',
            r'where (.+)',
            r'how far is (.+)',
            r'distance to (.+)',
            r'directions to (.+)',
            r'route to (.+)',
            r'எங்கே (.+)',
            r'எங்க (.+)',
            r'தூரம் (.+)',
            r'வழி (.+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return match.group(1).strip()
        
        # If no pattern matches, return the whole query cleaned up
        cleaned = re.sub(r'\b(where|is|how|far|distance|தூரம்|எங்கே|எங்க)\b', '', query, flags=re.IGNORECASE)
        return cleaned.strip()
    
    def _format_place_response(self, place: Place) -> str:
        """Format response for a single place"""
        location = gps_manager.get_current_location()
        
        if location:
            lat, lon = location
            distance = location_resolver.calculate_distance(lat, lon, place.latitude, place.longitude)
            location_summary = location_resolver.get_location_summary(place)
            
            if self.current_language == 'tamil':
                return f"{place.name} {location_summary} பகுதியில் இருக்கு. இங்கிருந்து சுமார் {distance} கி.மீ தூரம்."
            else:
                return f"{place.name} is in {location_summary}, about {distance} km from here."
        else:
            location_summary = location_resolver.get_location_summary(place)
            if self.current_language == 'tamil':
                return f"{place.name} {location_summary} பகுதியில் இருக்கு."
            else:
                return f"{place.name} is in {location_summary}."
    
    def _handle_multiple_matches(self, places: List[Place], query: str) -> str:
        """Handle multiple place matches"""
        if len(places) <= 3:
            # List the options
            options = []
            for place in places[:3]:
                summary = location_resolver.get_location_summary(place)
                options.append(f"{place.name} in {summary}")
            
            if self.current_language == 'tamil':
                return f"'{query}' என்று பல இடங்கள் கிடைத்தது. எந்தது வேண்டும்: {', '.join(options)}?"
            else:
                return f"I found multiple places named '{query}'. Did you mean: {', '.join(options)}?"
        else:
            if self.current_language == 'tamil':
                return f"'{query}' என்று நிறைய இடங்கள் இருக்கு. கொஞ்சம் தெளிவாக சொல்லுங்க."
            else:
                return f"Many places match '{query}'. Can you be more specific?"
    
    def _ask_clarification(self, message: str) -> str:
        """Ask for clarification in appropriate language"""
        if self.current_language == 'tamil':
            tamil_messages = {
                "What type of place are you looking for?": "என்ன வகையான இடம் தேடுகிறீர்கள்?",
                "Which place are you asking about?": "எந்த இடத்தைப் பற்றி கேட்கிறீர்கள்?",
                "Distance to which place?": "எந்த இடத்திற்கு தூரம்?",
                "Directions to where?": "எங்கே போக வழி வேண்டும்?"
            }
            return tamil_messages.get(message, message)
        return message
    
    def _check_internet(self) -> bool:
        """Check if internet is available"""
        try:
            import requests
            requests.get("https://nominatim.openstreetmap.org", timeout=3)
            return True
        except:
            return False
    
    def _get_offline_message(self) -> str:
        """Get offline message"""
        if self.current_language == 'tamil':
            return "Maps பயன்பாட்டுக்கு இணையம் தேவை. இணையம் வந்ததும் மீண்டும் முயற்சிக்கிறேன்."
        else:
            return "Maps requires internet. I'll try again when connection is available."
    
    def _get_location_error(self) -> str:
        """Get location access error message"""
        if self.current_language == 'tamil':
            return "Location access இல்லை. Settings-ல enable செய்யவா?"
        else:
            return "Location access is off — should I enable it?"

# Global instance
maps_assistant = MapsAssistant()