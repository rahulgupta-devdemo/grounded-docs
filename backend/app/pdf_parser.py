import re
from dataclasses import dataclass

import pymupdf

_TEXT_BLOCK = 0


@dataclass(frozen=True)
class Page:
    number: int  # 1-based position in the file, as shown by PDF viewers
    text: str


def extract_pages(pdf_bytes: bytes) -> list[Page]:
    """Return the text of every page; paragraphs are separated by a blank line."""
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        return [Page(number=i + 1, text=_page_text(page)) for i, page in enumerate(doc)]


def _page_text(page: pymupdf.Page) -> str:
    blocks = page.get_text("blocks", sort=True)
    paragraphs = (
        re.sub(r"\s+", " ", block[4]).strip()
        for block in blocks
        if block[6] == _TEXT_BLOCK
    )
    return "\n\n".join(p for p in paragraphs if p)
