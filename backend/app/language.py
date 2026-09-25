"""Detects whether a question is German or English.

Only these two are needed here, so a word list is enough and keeps the
result deterministic. Words that exist in both languages ("in", "an",
"was") are left out.
"""

import re

_GERMAN = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einer",
    "und", "oder", "ist", "sind", "hat", "haben", "wird", "werden", "kann",
    "darf", "muss", "gibt", "wie", "welche", "welcher", "welches", "welchen",
    "wer", "wo", "wann", "warum", "wieviel", "wie viele", "mit", "für", "von",
    "zu", "zum", "zur", "auf", "bei", "nicht", "auch", "nach", "aus", "über",
    "im", "ich", "wir", "sie", "es", "gilt", "beträgt",
}
_ENGLISH = {
    "the", "a", "is", "are", "was", "were", "what", "which", "who", "how",
    "why", "when", "where", "does", "do", "can", "should", "must", "has",
    "have", "with", "for", "of", "to", "on", "at", "and", "or", "not", "it",
    "be", "this", "that", "from", "by", "there", "many", "much", "allowed",
}
_UMLAUT = re.compile(r"[äöüß]", re.IGNORECASE)


def detect_language(text: str) -> str | None:
    """Return "German", "English", or None if unclear."""
    words = re.findall(r"\w+", text.lower())
    german = sum(w in _GERMAN for w in words) + 2 * len(_UMLAUT.findall(text))
    english = sum(w in _ENGLISH for w in words)
    if german > english:
        return "German"
    if english > german:
        return "English"
    return None
