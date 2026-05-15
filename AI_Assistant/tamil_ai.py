"""
JARVIS Tamil Support — clean rewrite without deleted dependencies.

Detects Tamil script and Tanglish keywords.
Routes Tamil queries through the main AI brain with Tamil context.
"""

from __future__ import annotations
import os
import re

_TAMIL_RANGE = ('\u0b80', '\u0bff')

# Common Tanglish (Tamil written in English) keywords
_TANGLISH = {
    'sollu', 'pannunga', 'kodu', 'vaanga', 'podu', 'eduthu', 'paaru',
    'enna', 'eppo', 'eppadi', 'yaar', 'enga', 'neram', 'mani', 'kaalam',
    'vaanilai', 'vilakku', 'paadal', 'paatu', 'nandri', 'vanakkam',
    'seri', 'okay', 'illa', 'irukku', 'theriyum', 'puriyala',
}


def has_tamil_script(text: str) -> bool:
    return any(_TAMIL_RANGE[0] <= ch <= _TAMIL_RANGE[1] for ch in text)


def has_tanglish(text: str) -> bool:
    words = set(text.lower().split())
    return len(words & _TANGLISH) >= 1


def detect_language(text: str) -> str:
    """Returns 'ta', 'en', or 'mixed'."""
    if not text:
        return 'en'
    if has_tamil_script(text):
        en_chars = sum(1 for c in text if c.isalpha() and c.isascii())
        return 'mixed' if en_chars > 5 else 'ta'
    if has_tanglish(text):
        return 'mixed'
    return 'en'


def inject_tamil_context(text: str) -> str:
    """Add Tamil language hint to query so AI responds in Tamil."""
    lang = detect_language(text)
    if lang in ('ta', 'mixed'):
        os.environ['JARVIS_STT_LANG'] = 'ta'
        return text  # AI brain already handles Tamil via system prompt
    else:
        os.environ['JARVIS_STT_LANG'] = 'en'
        return text


def get_tamil_tts_lang(text: str) -> str:
    """Return TTS language code for given text."""
    lang = detect_language(text)
    return 'ta' if lang in ('ta', 'mixed') else 'en'
