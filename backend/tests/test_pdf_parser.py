import pymupdf

from app.pdf_parser import extract_pages


def _make_pdf(pages: list[list[str]]) -> bytes:
    doc = pymupdf.open()
    for paragraphs in pages:
        page = doc.new_page()
        for i, paragraph in enumerate(paragraphs):
            page.insert_text((72, 72 + i * 200), paragraph)
    return doc.tobytes()


def test_extracts_text_per_page_with_1_based_numbers():
    pdf = _make_pdf([["Page one text."], ["Page two text."]])

    pages = extract_pages(pdf)

    assert [p.number for p in pages] == [1, 2]
    assert pages[0].text == "Page one text."
    assert pages[1].text == "Page two text."


def test_separates_blocks_with_blank_line():
    pdf = _make_pdf([["First block.", "Second block."]])

    assert extract_pages(pdf)[0].text == "First block.\n\nSecond block."


def test_page_without_text_returns_empty_string():
    pdf = _make_pdf([[]])

    assert extract_pages(pdf)[0].text == ""


def test_keeps_german_characters():
    pdf = _make_pdf([["Lichtstrom für Außenleuchten"]])

    assert extract_pages(pdf)[0].text == "Lichtstrom für Außenleuchten"
