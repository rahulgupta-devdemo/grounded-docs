"""Recognises greetings, acknowledgements and questions about the app itself,
which need no document search.

Only exact phrases count, so a short real question such as "IP66?" or an
article number on its own is still searched.
"""

import re

# Only words that are clearly German get a German reply; words used in both
# languages ("hi", "ok") get the English one.
_GERMAN = {
    "hallo", "servus", "moin", "guten tag", "guten morgen", "guten abend", "gute nacht",
    "wie gehts", "wie geht es dir", "wie geht es ihnen",
    "hilfe", "was kannst du", "was kannst du tun", "was können sie", "wer bist du",
    "danke", "danke schön", "danke schoen", "vielen dank", "tschüss", "tschuess",
    "ja", "nein", "gut", "super", "alles klar",
}
_ENGLISH = {
    "ok", "okay", "hi", "hey", "hello", "hey there", "good morning", "good evening", "good night",
    "how are you", "how are you doing", "whats up", "thanks", "thank you",
    "help", "what can you do", "what can i ask", "what can i ask you", "who are you",
    "thx", "bye", "goodbye", "ciao", "see you", "yes", "no", "great", "cool", "nice", "test",
}

_REPLIES = {
    "German": "Stellen Sie mir eine Frage zu Ihren Dokumenten, zum Beispiel zu einem Produkt, "
    "einem technischen Wert oder einer Seite. Jede Antwort nennt ihre Quellen.",
    "English": "Ask me a question about your documents, for example about a product, "
    "a technical value or a page. Every answer cites its sources.",
}


def small_talk_reply(text: str) -> str | None:
    """A reply if the text is only small talk or a question about the app, else None."""
    normalised = re.sub(r"[^\w\s]", "", text.lower()).strip()
    normalised = re.sub(r"\s+", " ", normalised)
    if normalised in _GERMAN:
        return _REPLIES["German"]
    if normalised in _ENGLISH:
        return _REPLIES["English"]
    return None
