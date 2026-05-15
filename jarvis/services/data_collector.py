"""
JARVIS Data Collector — weather via wttr.in + Wikipedia for info queries.
No API keys required.
"""

import logging
import re
import time
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

_CACHE: dict = {}
_CACHE_TTL = 600


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["value"]
    return None


def _cache_set(key: str, value):
    _CACHE[key] = {"value": value, "ts": time.time()}


def _extract_location(query: str) -> str:
    query = query.lower().strip()
    for pattern in (
        r"(?:weather|temperature|forecast|rain|climate)\s+(?:in|at|for|of)\s+([a-z][a-z\s]{1,30})",
        r"([a-z][a-z\s]{1,20})\s+(?:weather|temperature|forecast|climate)",
        r"(?:in|at|for)\s+([a-z][a-z\s]{1,30})",
    ):
        m = re.search(pattern, query)
        if m:
            loc = m.group(1).strip().rstrip(".")
            if loc not in {"the", "my", "our", "a", "an"}:
                return loc.title()
    return ""


def get_weather(query: str) -> str:
    location = _extract_location(query or "")
    cache_key = f"weather:{location or 'auto'}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    url_loc = location.replace(" ", "+") if location else ""
    try:
        resp = requests.get(
            f"https://wttr.in/{url_loc}?format=4&lang=en",
            timeout=6, headers={"User-Agent": "JARVIS-AI/1.0"},
        )
        if resp.status_code == 200:
            text = re.sub(r"[^\x20-\x7E\u00C0-\u017E]", "", resp.text.strip())
            text = re.sub(r"\s{2,}", " ", text)
            result = f"Weather in {location}: {text}" if location else f"Current weather: {text}"
            _cache_set(cache_key, result)
            return result
    except requests.Timeout:
        logger.warning("Weather request timed out")
    except requests.RequestException as e:
        logger.warning("Weather request failed: %s", e)

    # JSON fallback
    try:
        resp = requests.get(
            f"https://wttr.in/{url_loc}?format=j1",
            timeout=6, headers={"User-Agent": "JARVIS-AI/1.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            current = data["current_condition"][0]
            area = data.get("nearest_area", [{}])[0]
            city = (area.get("areaName", [{}])[0].get("value", "")) or location or "your area"
            result = (
                f"Weather in {city}: {current.get('weatherDesc', [{}])[0].get('value', '')}, "
                f"{current.get('temp_C', '?')}°C "
                f"(feels like {current.get('FeelsLikeC', '?')}°C), "
                f"humidity {current.get('humidity', '?')}%."
            )
            _cache_set(cache_key, result)
            return result
    except (requests.RequestException, KeyError, ValueError) as e:
        logger.warning("Weather JSON fallback failed: %s", e)

    return (
        f"I could not fetch the weather for {location} right now." if location
        else "Weather info is unavailable right now."
    )


def get_information(query: str) -> str:
    if not query:
        return "What would you like to know?"

    q = query.lower().strip()
    now = datetime.now()

    if any(w in q for w in ("what time", "current time", "time now")):
        return f"The current time is {now.strftime('%I:%M %p').lstrip('0')}."
    if any(w in q for w in ("what date", "today's date", "what day")):
        return f"Today is {now.strftime('%A, %B %d, %Y')}."

    calc = _try_calculate(q)
    if calc is not None:
        return f"The answer is {calc}."

    search_term = _extract_search_term(q)
    if not search_term:
        return "I need a bit more context. Could you rephrase it?"

    cache_key = f"wiki:{search_term}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    result = _wikipedia_search(search_term)
    if result:
        _cache_set(cache_key, result)
        return result

    return f"I could not find clear information about '{search_term}'."


def _try_calculate(text: str):
    """Safely evaluate simple math using AST — no eval()."""
    import ast
    import operator

    _OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.operand))
        raise ValueError(f"Unsupported node: {type(node)}")

    expr = re.sub(r"[^0-9+\-*/().\ ]", "", text).strip()
    if len(expr) < 3 or not re.search(r"[+\-*/]", expr):
        return None
    try:
        result = _eval(ast.parse(expr, mode="eval").body)
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        s = str(round(result, 6))
        return s.rstrip("0").rstrip(".") if "." in s else s
    except (ValueError, ZeroDivisionError, SyntaxError):
        return None


def _extract_search_term(query: str) -> str:
    fillers = (
        "what is", "what are", "who is", "who are", "tell me about",
        "explain", "how does", "how do", "define", "what does",
        "can you tell me", "jarvis", "please", "search for", "look up",
    )
    text = query.lower()
    for f in fillers:
        text = text.replace(f, "").strip()
    return re.sub(r"\s+", " ", text).strip(" ?.,!")


def _wikipedia_search(term: str, sentences: int = 2) -> str:
    if not term:
        return ""
    try:
        clean = requests.utils.quote(term.strip().replace(" ", "_"))
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean}",
            timeout=7, headers={"User-Agent": "JARVIS-AI/1.0"},
        )
        if resp.status_code == 200:
            extract = resp.json().get("extract", "")
            if extract:
                sents = re.split(r"(?<=[.!?])\s+", extract)
                return " ".join(sents[:sentences])
    except requests.RequestException as e:
        logger.warning("Wikipedia summary failed: %s", e)

    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": term,
                    "format": "json", "srlimit": 1},
            timeout=7, headers={"User-Agent": "JARVIS-AI/1.0"},
        )
        if resp.status_code == 200:
            results = resp.json().get("query", {}).get("search", [])
            if results:
                return _wikipedia_search(results[0]["title"], sentences)
    except requests.RequestException as e:
        logger.warning("Wikipedia search fallback failed: %s", e)

    return ""
