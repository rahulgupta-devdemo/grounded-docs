import pytest

from app.language import detect_language


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Who is allowed to install the luminaire?", "English"),
        ("What is the luminous flux?", "English"),
        ("How high should it be mounted?", "English"),
        ("Welche Schutzart hat die Leuchte?", "German"),
        ("Wie hoch ist der Lichtstrom?", "German"),
        ("Wer darf die Leuchte installieren?", "German"),
        ("Lichtpunkthöhe?", "German"),
        ("IP66?", None),
        ("5XA6231NA20", None),
    ],
)
def test_detect_language(question, expected):
    assert detect_language(question) == expected
