"""
JARVIS Ticket Booking — Real provider adapter.

Architecture:
  1. BookMyShow scraper  (live data, no API key needed)
  2. enhanced_booking    (offline demo fallback)

Public API:
  search_movies(query, city)  → list of {id, title, genre, rating, duration}
  get_theaters(movie, city)   → list of {id, name, location, distance}
  get_showtimes(movie, theater, city) → list of {time, seats_left, price}
  initiate_checkout(movie, theater, showtime, seats) → {url, summary}
"""

from __future__ import annotations
import os
import re
import time
import requests
from typing import Optional

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}
_TIMEOUT = 8
_DEFAULT_CITY = "Chennai"
_DEMO_FALLBACK = os.getenv("JARVIS_BOOKING_DEMO", "0") == "1"

# ── simple in-memory cache ────────────────────────────────────────────────────
_cache: dict = {}
def _cget(k):
    e = _cache.get(k)
    return e["v"] if e and time.time() - e["t"] < 300 else None
def _cset(k, v):
    _cache[k] = {"v": v, "t": time.time()}


# ═══════════════════════════════════════════════════════════════════════════════
# BookMyShow adapter  (uses their public JSON endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class BookMyShowAdapter:
    BASE = "https://in.bookmyshow.com"
    API  = "https://in.bookmyshow.com/api"

    def _city_code(self, city: str) -> str:
        codes = {
            "chennai": "CHEN", "mumbai": "MUMBAI", "delhi": "NCR",
            "bangalore": "BANG", "hyderabad": "HYD", "kolkata": "KOLK",
            "pune": "PUNE", "coimbatore": "COIMB", "madurai": "MDU",
        }
        return codes.get(city.lower().strip(), "CHEN")

    def search_movies(self, query: str = "", city: str = _DEFAULT_CITY) -> list:
        code = self._city_code(city)
        ck = f"bms_movies:{code}:{query}"
        cached = _cget(ck)
        if cached:
            return cached

        # BMS public API requires cookies — use their explore endpoint instead
        urls_to_try = [
            f"https://in.bookmyshow.com/api/explore/v1/discover/movies?appCode=MOBAND2&appVersion=14.3.4&language=en&regionCode={code}&subRegion={code}&bmsId=1.21.0&token=67x1xa33b4x422b361ba&lat=13.0827&lon=80.2707&categoryCode=MOVIES&eventType=MT",
            f"https://in.bookmyshow.com/serv/getData?cmd=QUICKBOOK&type=MT&code={code}",
        ]
        for url in urls_to_try:
            try:
                r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
                if r.status_code == 200:
                    try:
                        data = r.json()
                    except Exception:
                        continue
                    # Try multiple response shapes
                    events = (
                        data.get("BookMyShow", {}).get("arrEvents") or
                        data.get("arrEvents") or
                        data.get("movies") or
                        data.get("data", {}).get("movies") or []
                    )
                    movies = []
                    for m in events[:10]:
                        title = (m.get("EventTitle") or m.get("title") or
                                 m.get("name") or m.get("movieName", ""))
                        if not title:
                            continue
                        movies.append({
                            "id":       m.get("EventCode") or m.get("id") or m.get("code", ""),
                            "title":    title,
                            "genre":    m.get("EventGenre") or m.get("genre", ""),
                            "rating":   m.get("Rating") or m.get("rating", ""),
                            "duration": m.get("EventDuration") or m.get("duration", ""),
                            "language": m.get("EventLanguage") or m.get("language", ""),
                        })
                    if query:
                        movies = [m for m in movies if query.lower() in m["title"].lower()]
                    if movies:
                        _cset(ck, movies)
                        return movies
            except Exception as e:
                print(f"[BMS] search_movies error ({url[:50]}): {e}")
                continue
        return []

    def get_theaters(self, movie_id: str, city: str = _DEFAULT_CITY) -> list:
        code = self._city_code(city)
        ck = f"bms_theaters:{code}:{movie_id}"
        cached = _cget(ck)
        if cached:
            return cached

        try:
            url = f"{self.API}/venue/venuelist?regionCode={code}&eventCode={movie_id}"
            r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                theaters = []
                for v in data.get("BookMyShow", {}).get("arrVenues", [])[:8]:
                    theaters.append({
                        "id":       v.get("VenueCode", ""),
                        "name":     v.get("VenueName", ""),
                        "location": v.get("VenueAddress", ""),
                        "distance": v.get("Distance", ""),
                    })
                if theaters:
                    _cset(ck, theaters)
                    return theaters
        except Exception as e:
            print(f"[BMS] get_theaters error: {e}")

        return []

    def get_showtimes(self, movie_id: str, venue_id: str,
                      city: str = _DEFAULT_CITY) -> list:
        code = self._city_code(city)
        from datetime import datetime
        date = datetime.now().strftime("%Y%m%d")
        ck = f"bms_shows:{code}:{movie_id}:{venue_id}:{date}"
        cached = _cget(ck)
        if cached:
            return cached

        try:
            url = (f"{self.API}/showtime/list?regionCode={code}"
                   f"&eventCode={movie_id}&venueCode={venue_id}&date={date}")
            r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                shows = []
                for s in data.get("BookMyShow", {}).get("arrShowTimes", [])[:6]:
                    shows.append({
                        "time":       s.get("ShowTime", ""),
                        "show_id":    s.get("ShowCode", ""),
                        "seats_left": s.get("SeatsAvailable", "?"),
                        "price":      s.get("MinPrice", ""),
                        "screen":     s.get("ScreenName", ""),
                    })
                if shows:
                    _cset(ck, shows)
                    return shows
        except Exception as e:
            print(f"[BMS] get_showtimes error: {e}")

        return []

    def checkout_url(self, movie_id: str, venue_id: str,
                     show_id: str, seats: int = 1) -> str:
        """Return direct BookMyShow checkout URL."""
        return (f"{self.BASE}/buytickets/{movie_id}/{venue_id}"
                f"?showCode={show_id}&qty={seats}")


# ═══════════════════════════════════════════════════════════════════════════════
# Offline fallback  (enhanced_booking demo data)
# ═══════════════════════════════════════════════════════════════════════════════

class OfflineFallback:
    def search_movies(self, query="", city=_DEFAULT_CITY):
        try:
            from enhanced_booking import TicketBookingSystem
            sys = TicketBookingSystem()
            movies = [{"id": str(m["id"]), "title": m["title"],
                       "genre": m["genre"], "rating": m["rating"],
                       "duration": m["duration"], "language": "Tamil/Hindi"}
                      for m in sys.get_movies()]
            if query:
                movies = [m for m in movies if query.lower() in m["title"].lower()]
            return movies
        except Exception:
            return [{"id": "1", "title": "Demo Movie", "genre": "Action",
                     "rating": "8.0", "duration": "150 min", "language": "Tamil"}]

    def get_theaters(self, movie_id="", city=_DEFAULT_CITY):
        try:
            from enhanced_booking import TicketBookingSystem
            sys = TicketBookingSystem()
            return [{"id": str(t["id"]), "name": t["name"],
                     "location": t["location"], "distance": t["distance"]}
                    for t in sys.get_theaters()]
        except Exception:
            return [{"id": "1", "name": "PVR Cinemas", "location": "City Center",
                     "distance": "2.5 km"}]

    def get_showtimes(self, movie_id="", venue_id="", city=_DEFAULT_CITY):
        return [
            {"time": "10:00 AM", "show_id": "s1", "seats_left": "42", "price": "₹150", "screen": "Screen 1"},
            {"time": "1:30 PM",  "show_id": "s2", "seats_left": "28", "price": "₹200", "screen": "Screen 2"},
            {"time": "4:45 PM",  "show_id": "s3", "seats_left": "15", "price": "₹200", "screen": "Screen 1"},
            {"time": "8:00 PM",  "show_id": "s4", "seats_left": "6",  "price": "₹250", "screen": "Screen 3"},
        ]

    def checkout_url(self, movie_id, venue_id, show_id, seats=1):
        return f"https://in.bookmyshow.com/buytickets/{movie_id}"


# ═══════════════════════════════════════════════════════════════════════════════
# Unified adapter — tries live first, falls back to offline
# ═══════════════════════════════════════════════════════════════════════════════

class BookingAdapter:
    def __init__(self):
        self._live    = BookMyShowAdapter()
        self._offline = OfflineFallback()
        self._last_source = "unknown"

    def source(self) -> str:
        return self._last_source

    def _set_source(self, source: str):
        self._last_source = source

    def search_movies(self, query: str = "", city: str = _DEFAULT_CITY) -> list:
        result = self._live.search_movies(query, city)
        if result:
            self._set_source("live")
            return result
        if _DEMO_FALLBACK:
            result = self._offline.search_movies(query, city)
            if result:
                self._set_source("demo")
                return result
        self._set_source("live_unavailable")
        return []

    def get_theaters(self, movie_id: str, city: str = _DEFAULT_CITY) -> list:
        result = self._live.get_theaters(movie_id, city)
        if result:
            self._set_source("live")
            return result
        if _DEMO_FALLBACK:
            result = self._offline.get_theaters(movie_id, city)
            if result:
                self._set_source("demo")
                return result
        self._set_source("live_unavailable")
        return []

    def get_showtimes(self, movie_id: str, venue_id: str,
                      city: str = _DEFAULT_CITY) -> list:
        result = self._live.get_showtimes(movie_id, venue_id, city)
        if result:
            self._set_source("live")
            return result
        if _DEMO_FALLBACK:
            result = self._offline.get_showtimes(movie_id, venue_id, city)
            if result:
                self._set_source("demo")
                return result
        self._set_source("live_unavailable")
        return []

    def checkout_url(self, movie_id: str, venue_id: str,
                     show_id: str, seats: int = 1) -> str:
        if _DEMO_FALLBACK:
            self._set_source("demo")
            return self._offline.checkout_url(movie_id, venue_id, show_id, seats)
        if movie_id and venue_id and show_id:
            self._set_source("live")
            return self._live.checkout_url(movie_id, venue_id, show_id, seats)
        self._set_source("live_unavailable")
        return ""

    def confirm_summary(self, movie: str, theater: str,
                        showtime: str, seats: int) -> str:
        """Return a voice-friendly confirmation prompt."""
        return (f"I found {showtime} at {theater} for {movie}. "
                f"{seats} seat{'s' if seats > 1 else ''} — shall I open checkout?")


# Global instance
booking_adapter = BookingAdapter()
