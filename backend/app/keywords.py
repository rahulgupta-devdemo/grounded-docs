"""Keyword vectors for hybrid search.

Every distinct word of a text becomes one dimension of a sparse vector (the
dimension is a hash of the word), weighted by how often it occurs, with the
saturation used in BM25. Qdrant multiplies each weight by the word's inverse
document frequency (IDF), so rare words such as article numbers count far
more than common ones. Semantic search misses exact identifiers; keyword
search misses paraphrases and other languages; hybrid search combines both.
"""

import re
import zlib
from collections import Counter

from qdrant_client import models

_WORD = re.compile(r"\w+")
_K1 = 1.2  # BM25 term-frequency saturation


def keyword_vector(text: str) -> models.SparseVector:
    """Weighted word vector for a stored passage."""
    weights: dict[int, float] = {}
    for word, count in _words(text).items():
        index = _index(word)
        # Two words can hash to the same index; their weights are added.
        weights[index] = weights.get(index, 0.0) + count * (_K1 + 1) / (count + _K1)
    return _sparse(weights)


def query_vector(text: str) -> models.SparseVector:
    """Word vector for a question: every distinct word once, weight 1."""
    return _sparse({_index(word): 1.0 for word in _words(text)})


def _words(text: str) -> Counter[str]:
    # Single characters are dropped: they carry no meaning and PDF layouts
    # produce many of them (spaced-out headings, table fragments).
    return Counter(w for w in _WORD.findall(text.lower()) if len(w) > 1)


def _index(word: str) -> int:
    return zlib.crc32(word.encode())


def _sparse(weights: dict[int, float]) -> models.SparseVector:
    return models.SparseVector(indices=list(weights), values=list(weights.values()))
