import pytest

from app.pdf_parser import InvalidPdfError, extract_pages


def test_extracts_text_per_page_with_1_based_numbers(make_pdf):
    pages = extract_pages(make_pdf([["Page one text."], ["Page two text."]]))

    assert [p.number for p in pages] == [1, 2]
    assert pages[0].text == "Page one text."
    assert pages[1].text == "Page two text."


def test_separates_blocks_with_blank_line(make_pdf):
    pdf = make_pdf([["First block.", "Second block."]])

    assert extract_pages(pdf)[0].text == "First block.\n\nSecond block."


def test_page_without_text_returns_empty_string(make_pdf):
    assert extract_pages(make_pdf([[]]))[0].text == ""


def test_keeps_german_characters(make_pdf):
    pdf = make_pdf([["Lichtstrom für Außenleuchten"]])

    assert extract_pages(pdf)[0].text == "Lichtstrom für Außenleuchten"


def test_rejects_bytes_that_are_not_a_pdf():
    with pytest.raises(InvalidPdfError):
        extract_pages(b"this is not a pdf")
