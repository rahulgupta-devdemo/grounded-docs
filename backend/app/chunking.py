import re
from dataclasses import dataclass

from app.pdf_parser import Page

_SENTENCE_END = re.compile(r"[.!?]\s")
_WHITESPACE = re.compile(r"\s")


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int
    index: int  # position within the whole document


def chunk_pages(pages: list[Page], size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        for text in split_text(page.text, size, overlap):
            chunks.append(Chunk(text=text, page=page.number, index=len(chunks)))
    return chunks


def split_text(text: str, size: int, overlap: int) -> list[str]:
    """Split text into windows of at most `size` characters.

    Each cut is moved back to the nearest paragraph break, else sentence end,
    else space. The next window starts `overlap` characters before the cut,
    aligned to the start of a word.
    """
    if not 0 <= overlap < size // 2:
        raise ValueError("overlap must be at least 0 and less than half of size")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            end = _best_break(text, start, end)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = _next_start(text, end, overlap)
    return chunks


def _best_break(text: str, start: int, end: int) -> int:
    # Only look in the second half of the window, so chunks never get tiny.
    min_end = start + (end - start) // 2
    window = text[min_end:end]

    paragraph = window.rfind("\n\n")
    if paragraph != -1:
        return min_end + paragraph

    sentence_ends = list(_SENTENCE_END.finditer(window))
    if sentence_ends:
        return min_end + sentence_ends[-1].start() + 1

    space = window.rfind(" ")
    if space != -1:
        return min_end + space

    return end


def _next_start(text: str, end: int, overlap: int) -> int:
    pos = end - overlap
    if overlap == 0 or text[pos - 1].isspace():
        return pos
    # Move forward to the next word start, but never past the previous cut,
    # otherwise text between the cut and that word would be lost.
    space = _WHITESPACE.search(text, pos, end)
    return space.end() if space else end
