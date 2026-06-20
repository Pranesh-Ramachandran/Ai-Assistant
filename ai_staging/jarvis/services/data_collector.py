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
    import math

    _OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
    }

    _FUNCS = {
        "sqrt": math.sqrt,
    }

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in _FUNCS and len(node.args) == 1:
                return _FUNCS[func_name](_eval(node.args[0]))
        raise ValueError(f"Unsupported node: {type(node)}")

    # Pre-parse/translate natural language math
    expr = text.lower().strip()
    
    # "square root of X" -> "sqrt(X)"
    expr = re.sub(r"square\s+root\s+of\s+([0-9.]+)", r"sqrt(\1)", expr)
    expr = re.sub(r"sqrt\s+of\s+([0-9.]+)", r"sqrt(\1)", expr)
    
    # "X percent of Y" -> "(X / 100 * Y)"
    expr = re.sub(r"([0-9.]+)\s*(?:percent|%)\s+of\s+([0-9.]+)", r"(\1 / 100 * \2)", expr)
    
    # "X percent" -> "(X / 100)"
    expr = re.sub(r"([0-9.]+)\s*(?:percent|%)", r"(\1 / 100)", expr)
    
    # "X mod Y" or "X modulo Y" -> "X % Y"
    expr = re.sub(r"\bmod(?:ulo)?\b", "%", expr)

    # Clean character selection — allow digits, operators, parenthesises, and function names
    expr = re.sub(r"[^0-9+\-*/().\s%sqrt]", "", expr).strip()
    
    if len(expr) < 1:
        return None
        
    try:
        parsed = ast.parse(expr, mode="eval").body
        result = _eval(parsed)
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        s = str(round(result, 6))
        return s.rstrip("0").rstrip(".") if "." in s else s
    except (ValueError, ZeroDivisionError, SyntaxError, TypeError):
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


def get_news_headlines() -> str:
    """Fetch top news headlines from Google News RSS using built-in ElementTree."""
    import xml.etree.ElementTree as ET
    cache_key = "news_headlines"
    cached = _cache_get(cache_key)
    if cached:
        return cached
        
    try:
        resp = requests.get(
            "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
            timeout=7,
            headers={"User-Agent": "JARVIS-AI/1.0"}
        )
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            titles = []
            for item in root.findall(".//item")[:5]:
                title = item.find("title").text
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                titles.append(f"• {title}")
            if titles:
                result = "Here are the top news headlines right now:\n" + "\n".join(titles)
                _cache_set(cache_key, result)
                return result
    except Exception as e:
        logger.warning("Failed to fetch RSS news: %s", e)
        
    return "I could not fetch the latest news headlines right now."
