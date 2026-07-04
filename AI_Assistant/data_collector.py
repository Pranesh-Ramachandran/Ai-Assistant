"""
Data Collector - Real weather via wttr.in + Wikipedia for info queries.
100% free, no API keys required.
"""

import re
import time
from datetime import datetime

import requests

# ─── Simple in-memory cache ───────────────────────────────────────────────────
_CACHE: dict = {}
_CACHE_TTL = 600  # seconds (10 min)


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["value"]
    return None


def _cache_set(key: str, value):
    _CACHE[key] = {"value": value, "ts": time.time()}


# ─── Location helpers ─────────────────────────────────────────────────────────

def _extract_location(query: str) -> str:
    """Pull a city/place name from a weather query."""
    query = query.lower().strip()

    # Patterns like "weather in Chennai", "Chennai weather", "weather at Mumbai"
    # Order matters - most specific first to avoid partial matches
    for pattern in (
        # "weather [today/tonight/now] in/at/on/for/of Location"
        r"(?:weather|temperature|forecast|rain|climate)(?:\s+(?:today|tonight|now|tomorrow|tomorrow night))?\s+(?:in|at|for|of|on)\s+([a-z][a-z\s]{1,30})",
        # "Location weather/temperature/forecast"
        r"([a-z][a-z\s]{1,20})\s+(?:weather|temperature|forecast|climate)",
        # "in/at/on/for Location" (but only if not preceded by "today/tonight/now")
        r"(?<!\w)(?:in|at|for|on)\s+([a-z][a-z\s]{1,30})(?!\s+(?:today|tonight|now|tomorrow))",
    ):
        m = re.search(pattern, query)
        if m:
            loc = m.group(1).strip().rstrip(".,")
            if loc and loc not in {"the", "my", "our", "a", "an", "is", "weather", "today", "now", "tomorrow"}:
                return loc.title()

    return ""


# ─── Weather ──────────────────────────────────────────────────────────────────

def get_weather(query: str) -> str:
    """
    Fetch real weather from wttr.in (free, no API key).
    Returns a human-readable string.
    """
    location = _extract_location(query or "")
    cache_key = f"weather:{location or 'auto'}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    url_loc = location.replace(" ", "+") if location else ""
    url = f"https://wttr.in/{url_loc}?format=4&lang=en"

    try:
        resp = requests.get(url, timeout=6, headers={"User-Agent": "JARVIS-AI/1.0"})
        if resp.status_code == 200:
            text = resp.text.strip()
            # wttr.in format=4 → "City: ⛅ +24°C ↗14km/h 65%"
            # Split on first colon to preserve city name, clean only the weather part
            if ":" in text:
                city_part, weather_part = text.split(":", 1)
            else:
                city_part, weather_part = "", text

            # Replace weather emoji with readable text
            for emoji, word in [
                ("⛅", "partly cloudy"), ("☀️", "sunny"), ("🌤️", "mostly sunny"),
                ("⛈️", "thunderstorm"), ("🌧️", "rainy"), ("❄️", "snowy"),
                ("🌩️", "thunderstorm"), ("🌨️", "snowy"), ("🌦️", "light rain"),
                ("🌫️", "foggy"), ("🌬️", "windy"),
            ]:
                weather_part = weather_part.replace(emoji, word)

            # Replace directional arrows with wind direction words
            for arrow, direction in [
                ("↗", "NE"), ("→", "E"), ("↘", "SE"), ("↓", "S"),
                ("↙", "SW"), ("←", "W"), ("↖", "NW"), ("↑", "N"),
            ]:
                weather_part = weather_part.replace(arrow, f"wind {direction}")

            weather_part = weather_part.replace("°C", " degrees Celsius")
            weather_part = weather_part.replace("°F", " degrees Fahrenheit")
            weather_part = weather_part.replace("°", " degrees")
            weather_part = re.sub(r"(\d+)\s*km/h", r"\1 kilometers per hour", weather_part)
            weather_part = weather_part.replace("km/h", "kilometers per hour")
            weather_part = re.sub(r"(\d+)\s*mph", r"\1 miles per hour", weather_part)
            weather_part = weather_part.replace("%", " percent")

            # Strip remaining non-ASCII from weather part only
            weather_part = ''.join(c if ord(c) < 128 else " " for c in weather_part)
            weather_part = re.sub(r"\s{2,}", " ", weather_part).strip()

            display_city = location or city_part.strip() or "your area"
            result = f"Weather in {display_city}: {weather_part}"
            _cache_set(cache_key, result)
            return result
    except requests.Timeout:
        pass
    except Exception:
        pass

    # Fallback — try JSON endpoint
    try:
        json_url = f"https://wttr.in/{url_loc}?format=j1"
        resp = requests.get(json_url, timeout=6, headers={"User-Agent": "JARVIS-AI/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            current = data["current_condition"][0]
            area = data.get("nearest_area", [{}])[0]
            city = (area.get("areaName", [{}])[0].get("value", "")) or location or "your area"
            temp_c = current.get("temp_C", "?")
            feels = current.get("FeelsLikeC", "?")
            desc = current.get("weatherDesc", [{}])[0].get("value", "")
            humidity = current.get("humidity", "?")
            result = (
                f"Weather in {city}: {desc}, {temp_c}°C "
                f"(feels like {feels}°C), humidity {humidity}%."
            )
            _cache_set(cache_key, result)
            return result
    except Exception:
        pass

    if location:
        return f"I could not fetch the weather for {location} right now. Please check your internet connection."
    return "Weather info is unavailable right now. Please check your internet connection."


# --- News -------------------------------------------------------------------

def get_news(category: str = "world") -> str:
    """Fetch top headlines from BBC RSS (free, no API key)."""
    feeds = {
        "world":      "http://feeds.bbci.co.uk/news/world/rss.xml",
        "india":      "http://feeds.bbci.co.uk/news/world/south_asia/rss.xml",
        "technology": "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "business":   "http://feeds.bbci.co.uk/news/business/rss.xml",
        "science":    "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    }
    cat = category.lower().strip()
    if any(w in cat for w in ("tech",)):           cat = "technology"
    elif any(w in cat for w in ("india", "south")): cat = "india"
    elif any(w in cat for w in ("business", "finance", "economy")): cat = "business"
    elif any(w in cat for w in ("science", "health")): cat = "science"
    else: cat = "world"

    cache_key = f"news:{cat}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        resp = requests.get(feeds[cat], timeout=7, headers={"User-Agent": "JARVIS-AI/1.0"})
        if resp.status_code != 200:
            return "Could not fetch news right now."
        titles = re.findall(r"<title><!\[CDATA\[(.+?)\]\]></title>", resp.text)
        if not titles:
            titles = re.findall(r"<title>([^<]{10,})</title>", resp.text)
        headlines = [t.strip() for t in titles[1:6] if t.strip()]
        if not headlines:
            return "No headlines found right now."
        result = f"Top {cat} news: " + ". ".join(headlines) + "."
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return f"Could not fetch news: {e}"



# ─── Information / Wikipedia ───────────────────────────────────────────────────

def get_information(query: str) -> str:
    """
    Answer general information queries using Wikipedia (free, no API key).
    Falls back to a friendly reply for time/date/greeting queries.
    """
    if not query:
        return "What would you like to know?"

    query_lower = query.lower().strip()

    # Fast local answers first
    now = datetime.now()
    if any(w in query_lower for w in ("what time", "current time", "time now", "mani enna")):
        return f"The current time is {now.strftime('%I:%M %p').lstrip('0')}."

    if any(w in query_lower for w in ("what date", "today's date", "what day", "today's day")):
        return f"Today is {now.strftime('%A, %B %d, %Y')}."

    if any(w in query_lower for w in ("hello", "hi", "hey", "vanakkam")):
        return "Hello! How can I help you?"

    # Try math/simple calculation
    calc_result = _try_calculate(query_lower)
    if calc_result is not None:
        return f"The answer is {calc_result}."

    # Wikipedia lookup
    search_term = _extract_search_term(query_lower)
    if not search_term:
        return "I need a bit more context to answer that. Could you rephrase it?"

    cache_key = f"wiki:{search_term}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    result = _wikipedia_search(search_term)
    if result:
        _cache_set(cache_key, result)
        return result

    return f"I could not find clear information about '{search_term}'. Try rephrasing or asking something more specific."


def _try_calculate(text: str) -> str | None:
    """Try to evaluate simple math expressions safely."""
    # Strip to just math-like characters
    expr = re.sub(r"[^0-9+\-*/().\s]", "", text).strip()
    if not expr or len(expr) < 3:
        return None
    # Only try if it looks like a real expression (has an operator)
    if not re.search(r"[+\-*/]", expr):
        return None
    try:
        # Restrict allowed names to builtins for safety
        result = eval(expr, {"__builtins__": {}})  # noqa: S307
        if isinstance(result, (int, float)):
            return str(round(result, 6)).rstrip("0").rstrip(".") if "." in str(result) else str(result)
    except Exception:
        pass
    return None


def _extract_search_term(query: str) -> str:
    """Extract the core search topic from a query string."""
    # Remove filler phrases
    fillers = (
        "what is", "what are", "who is", "who are", "tell me about",
        "explain", "how does", "how do", "give me info on", "information about",
        "define", "what does", "can you tell me", "jarvis", "please",
        "i want to know about", "search for", "look up",
    )
    text = query.lower()
    for filler in fillers:
        text = text.replace(filler, "").strip()

    text = re.sub(r"\s+", " ", text).strip(" ?.,!")
    return text


def _wikipedia_search(term: str, sentences: int = 2) -> str:
    """Use Wikipedia REST API (free) to get a short summary."""
    if not term:
        return ""
    try:
        # Wikipedia REST summary endpoint — no library needed, just requests
        clean = term.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(clean)}"
        resp = requests.get(url, timeout=7, headers={"User-Agent": "JARVIS-AI/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            extract = data.get("extract", "")
            if extract:
                # Take first N sentences
                sents = re.split(r"(?<=[.!?])\s+", extract)
                return " ".join(sents[:sentences])
    except Exception:
        pass

    # Fallback: Wikipedia search API
    try:
        search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": term,
            "format": "json",
            "srlimit": 1,
        }
        resp = requests.get(search_url, params=params, timeout=7,
                            headers={"User-Agent": "JARVIS-AI/1.0"})
        if resp.status_code == 200:
            results = resp.json().get("query", {}).get("search", [])
            if results:
                page_title = results[0]["title"]
                return _wikipedia_search(page_title, sentences)
    except Exception:
        pass

    return ""