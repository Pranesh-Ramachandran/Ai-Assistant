"""
Location Resolver - Privacy-respecting place lookup using OpenStreetMap
Simple, conversational, bilingual location assistance
"""

import requests
import json
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class Place:
    name: str
    display_name: str
    latitude: float
    longitude: float
    category: str = ""
    confidence: float = 1.0

class LocationResolver:
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.timeout = 5
        self.cache = {}  # Simple cache for recent queries
        self.user_agent = "JarvisAI/1.0"
        
    def search_place(self, query: str, limit: int = 5) -> List[Place]:
        """Search for places using Nominatim"""
        try:
            # Check cache first
            cache_key = query.lower().strip()
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            params = {
                'q': query,
                'format': 'json',
                'limit': limit,
                'addressdetails': 1,
                'extratags': 1
            }
            
            headers = {'User-Agent': self.user_agent}
            response = requests.get(self.base_url, params=params, 
                                  headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                results = response.json()
                places = []
                
                for result in results:
                    place = Place(
                        name=result.get('name', query),
                        display_name=result.get('display_name', ''),
                        latitude=float(result.get('lat', 0)),
                        longitude=float(result.get('lon', 0)),
                        category=result.get('category', ''),
                        confidence=float(result.get('importance', 0.5))
                    )
                    places.append(place)
                
                # Cache results
                self.cache[cache_key] = places
                return places
            
        except Exception as e:
            print(f"Location search error: {e}")
        
        return []
    
    def find_nearby(self, category: str, lat: float, lon: float, radius: int = 5000) -> List[Place]:
        """Find nearby places of specific category"""
        try:
            # Use Overpass API for nearby search
            overpass_url = "https://overpass-api.de/api/interpreter"
            
            # Map common categories to OSM tags
            category_map = {
                'hospital': 'amenity=hospital',
                'atm': 'amenity=atm',
                'restaurant': 'amenity=restaurant',
                'hotel': 'tourism=hotel',
                'petrol': 'amenity=fuel',
                'school': 'amenity=school',
                'college': 'amenity=college',
                'bank': 'amenity=bank',
                'pharmacy': 'amenity=pharmacy'
            }
            
            osm_tag = category_map.get(category.lower(), f'name~"{category}"')
            
            query = f"""
            [out:json][timeout:5];
            (
              node[{osm_tag}](around:{radius},{lat},{lon});
              way[{osm_tag}](around:{radius},{lat},{lon});
            );
            out center;
            """
            
            response = requests.post(overpass_url, data=query, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                places = []
                
                for element in data.get('elements', []):
                    if 'tags' in element and 'name' in element['tags']:
                        # Get coordinates
                        if element['type'] == 'node':
                            place_lat = element['lat']
                            place_lon = element['lon']
                        elif 'center' in element:
                            place_lat = element['center']['lat']
                            place_lon = element['center']['lon']
                        else:
                            continue
                        
                        place = Place(
                            name=element['tags']['name'],
                            display_name=element['tags'].get('name', ''),
                            latitude=place_lat,
                            longitude=place_lon,
                            category=category
                        )
                        places.append(place)
                
                # Sort by distance
                places.sort(key=lambda p: self.calculate_distance(lat, lon, p.latitude, p.longitude))
                return places[:5]  # Return top 5
                
        except Exception as e:
            print(f"Nearby search error: {e}")
        
        return []
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance using Haversine formula (returns km)"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        return round(distance, 1)
    
    def get_location_summary(self, place: Place) -> str:
        """Get a brief location summary from display name"""
        parts = place.display_name.split(',')
        if len(parts) >= 2:
            # Return city/district info
            return parts[-2].strip() + ", " + parts[-1].strip()
        return place.display_name
    
    def clear_cache(self):
        """Clear the search cache"""
        self.cache.clear()

# Global instance
location_resolver = LocationResolver()