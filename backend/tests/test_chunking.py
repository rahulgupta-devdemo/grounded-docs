import pytest

from app.chunking import chunk_pages, split_text
from app.pdf_parser import Page

WORDS = [f"word{i}" for i in range(400)]
LONG_TEXT = " ".join(WORDS)


def test_short_text_is_one_chunk():
    assert split_text("Luminous flux 4200 lm.", size=100, overlap=10) == [
        "Luminous flux 4200 lm."
    ]


def test_empty_text_gives_no_chunks():
    assert split_text("   ", size=100, overlap=10) == []


def test_chunks_respect_max_size():
    chunks = split_text(LONG_TEXT, size=200, overlap=40)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


def test_no_text_is_lost():
    chunks = split_text(LONG_TEXT, size=200, overlap=40)
    covered = set(" ".join(chunks).split())
    assert covered == set(WORDS)


def test_words_are_never_cut():
    chunks = split_text(LONG_TEXT, size=200, overlap=40)
    for chunk in chunks:
        assert set(chunk.split()) <= set(WORDS)


def test_consecutive_chunks_overlap():
    chunks = split_text(LONG_TEXT, size=200, overlap=40)
    for current, following in zip(chunks, chunks[1:]):
        first_word = following.split()[0]
        assert first_word in current.split()


def test_cut_prefers_sentence_end():
    text = "A" * 50 + ". " + "b " * 60
    first = split_text(text, size=100, overlap=10)[0]
    assert first.endswith(".")


def test_cut_prefers_paragraph_break():
    text = "First paragraph. " * 4 + "\n\n" + "Second paragraph text. " * 5
    first = split_text(text, size=120, overlap=10)[0]
    assert first == ("First paragraph. " * 4).strip()


def test_early_paragraph_break_is_ignored_to_avoid_tiny_chunks():
    text = "Short.\n\n" + "Long sentence here. " * 10
    first = split_text(text, size=120, overlap=10)[0]
    assert len(first) > 60


def test_text_without_spaces_still_terminates_without_loss():
    text = "x" * 1000
    chunks = split_text(text, size=100, overlap=20)
    assert "".join(chunks) == text


def test_invalid_overlap_is_rejected():
    with pytest.raises(ValueError):
        split_text("text", size=100, overlap=50)


def test_chunk_pages_keeps_page_numbers_and_skips_empty_pages():
    pages = [
        Page(number=1, text="Intro page."),
        Page(number=2, text=""),
        Page(number=3, text=LONG_TEXT),
    ]
    chunks = chunk_pages(pages, size=200, overlap=40)

    assert chunks[0].page == 1
    assert {c.page for c in chunks} == {1, 3}
    assert [c.index for c in chunks] == list(range(len(chunks)))
