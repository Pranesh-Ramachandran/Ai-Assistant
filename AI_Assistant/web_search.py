"""
Web Search - Tier 3 Feature
Fallback web search for low-confidence queries and real-time information.

Examples:
  "What's the latest news on AI?"
  "Search for best restaurants nearby"
  "Find information about quantum computing"
  "How's the weather in Tokyo?" (when WeatherAPI unavailable)
"""

import re
import json
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime


class WebSearchManager:
    """
    Manages web search queries and result processing.
    Provides fallback search for low-confidence responses.
    """
    
    def __init__(self):
        """Initialize web search manager."""
        self.search_config = self._load_config()
        self.search_cache = {}
        self.last_search = None
        self.search_mode = "safe"  # safe or open
    
    def _load_config(self) -> Dict[str, Any]:
        """Load search configuration."""
        config_file = os.path.join(os.path.dirname(__file__), ".search_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "search_provider": "duckduckgo",  # or "google", "bing"
            "result_count": 5,
            "timeout": 10,
            "safe_search": True,
            "language": "en",
            "location": None
        }
    
    def is_searchable_query(self, query: str) -> bool:
        """
        Determine if query should use web search.
        
        Searchable queries: facts, news, current info, definitions
        Non-searchable: personal info, device control, math
        """
        non_searchable_patterns = [
            r"turn on|turn off|switch",  # Device control
            r"my (name|location|number|password|credit card)",  # Personal
            r"calculate|compute|\d+\+\d+",  # Math
            r"remind me|set alarm|timer",  # Device functions
        ]
        
        for pattern in non_searchable_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return False
        
        # Check if query looks like information seeking
        info_patterns = [
            r"what is|who is|how to|when did",
            r"latest|news|today",
            r"definition|meaning|explain",
            r"near me|nearby|closest",
            r"best|top|recommended"
        ]
        
        for pattern in info_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        
        # Default: searchable if asking "how" or contains specific topics
        return any(w in query.lower() for w in ["how", "what", "where", "when", "why", "news", "information"])
    
    def extract_search_parameters(self, query: str) -> Dict[str, Any]:
        """
        Extract search parameters from natural language query.
        
        Returns: {
            "query": str,
            "search_type": "general|news|local|academic",
            "location": str,
            "filters": dict
        }
        """
        result = {
            "query": query,
            "search_type": "general",
            "location": None,
            "filters": {}
        }
        
        # Detect search type
        if any(w in query.lower() for w in ["news", "latest", "today", "happening"]):
            result["search_type"] = "news"
        elif any(w in query.lower() for w in ["near me", "nearby", "closest", "restaurants", "hotels"]):
            result["search_type"] = "local"
        elif any(w in query.lower() for w in ["research", "academic", "study", "peer-reviewed"]):
            result["search_type"] = "academic"
        
        # Extract location
        location_match = re.search(r"in\s+([a-zA-Z\s]+?)(?:\s+(?:near|to|around|restaurants|hotels))?(?:\s|$)", query, re.IGNORECASE)
        if location_match:
            result["location"] = location_match.group(1).strip()
        
        # Extract filters
        if "price" in query.lower():
            if "cheap" in query.lower() or "budget" in query.lower():
                result["filters"]["price"] = "budget"
            elif "expensive" in query.lower() or "premium" in query.lower():
                result["filters"]["price"] = "premium"
        
        # Extract time filter
        if any(w in query.lower() for w in ["this week", "last month", "past year"]):
            result["filters"]["recency"] = "recent"
        
        return result
    
    def format_search_result(self, title: str, snippet: str, url: str = "", 
                            source: str = "", timestamp: str = "") -> Dict[str, str]:
        """Format search result for display."""
        return {
            "title": title,
            "snippet": snippet[:160] + "..." if len(snippet) > 160 else snippet,
            "url": url,
            "source": source,
            "timestamp": timestamp
        }
    
    def parse_search_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """
        Parse and clean search results.
        
        Removes duplicates, ads, formats for voice output.
        """
        formatted = []
        seen_snippets = set()
        
        for result in results:
            snippet = result.get("snippet", "")
            
            # Skip ads and duplicates
            if snippet in seen_snippets or len(snippet) < 20:
                continue
            
            seen_snippets.add(snippet)
            formatted.append({
                "title": result.get("title", ""),
                "snippet": snippet,
                "source": result.get("source", ""),
                "url": result.get("url", "")
            })
        
        return formatted[:5]  # Top 5 results
    
    def generate_summary_from_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Generate voice-friendly summary from search results.
        
        Combines information from top results.
        """
        if not results:
            return "No results found. Try a different search."
        
        summaries = []
        for i, result in enumerate(results[:3], 1):
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            
            # Extract key information
            if i == 1:
                summary = f"{title}. {snippet}"
            else:
                summary = snippet
            
            summaries.append(summary)
        
        return " ".join(summaries)
    
    def handle_search_result_followup(self, result: Dict[str, Any]) -> str:
        """Generate follow-up prompt after search result."""
        return "Would you like more information, or should I search for something else?"
    
    def cache_search_result(self, query: str, results: List[Dict[str, Any]]) -> None:
        """Cache search results for quick access."""
        query_key = query.lower().strip()
        self.search_cache[query_key] = {
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "access_count": 0
        }
    
    def get_cached_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached search results (valid for 1 hour)."""
        query_key = query.lower().strip()
        
        if query_key not in self.search_cache:
            return None
        
        cached = self.search_cache[query_key]
        cached["access_count"] += 1
        
        # Check if cache is still valid (1 hour)
        cache_time = datetime.fromisoformat(cached["timestamp"])
        if (datetime.now() - cache_time).seconds > 3600:
            del self.search_cache[query_key]
            return None
        
        return cached["results"]
    
    def handle_search_query(self, query: str, fallback: bool = False) -> Dict[str, Any]:
        """
        Handle web search query.
        
        fallback=True when used as fallback for low-confidence responses.
        """
        
        # Check cache first
        cached = self.get_cached_search(query)
        if cached:
            return {
                "success": True,
                "source": "cache",
                "query": query,
                "results": cached,
                "message": "Search results (from cache):"
            }
        
        # Extract parameters
        params = self.extract_search_parameters(query)
        
        # Mock search results (real implementation would call API)
        mock_results = [
            self.format_search_result(
                "About Topic",
                f"{query} refers to the practice of... (Mock result)",
                "https://example1.com"
            ),
            self.format_search_result(
                "Recent News",
                f"Latest developments in {query}... (Mock result)",
                "https://example2.com"
            ),
            self.format_search_result(
                "Information",
                f"Key facts about {query}... (Mock result)",
                "https://example3.com"
            ),
        ]
        
        # Parse and cache
        formatted_results = self.parse_search_results(mock_results)
        self.cache_search_result(query, formatted_results)
        self.last_search = query
        
        return {
            "success": True,
            "source": "web",
            "query": query,
            "search_type": params.get("search_type"),
            "results": formatted_results,
            "summary": self.generate_summary_from_results(formatted_results),
            "fallback": fallback,
            "message": f"Found {len(formatted_results)} results for '{query}'"
        }


# Singleton instance
WEB_SEARCH = WebSearchManager()


def handle_web_search(query: str, fallback: bool = False) -> Dict[str, Any]:
    """
    Public function to handle web search.
    
    Usage:
      handle_web_search("What's AI?")
      handle_web_search("Latest news on Python", fallback=True)
    """
    
    # Check if query is searchable
    if not WEB_SEARCH.is_searchable_query(query):
        return {
            "success": False,
            "message": f"This query isn't suitable for web search. I can help you directly with this."
        }
    
    return WEB_SEARCH.handle_search_query(query, fallback=fallback)
