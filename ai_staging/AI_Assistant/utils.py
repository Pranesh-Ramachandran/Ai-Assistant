# utils.py
import requests

def check_internet(timeout=3):
    """Return True if internet is reachable, False otherwise."""
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except requests.RequestException:
        return False
