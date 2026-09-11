"""Minimal local knowledge retrieval (RAG support infrastructure).

Dependency-free, offline, zero-egress. A plain-text corpus (``.txt`` files)
is chunked by paragraph and ranked against a query with a small local
BM25-style scorer. No embeddings, no vector database, no cloud services, and
no new dependencies — only the Python standard library.

The module implements the existing ``ai_agent.rag.retriever.Retriever``
interface so the orchestrator can use it without structural changes.

Security principle: retrieved text is strictly *untrusted data*. Chunks are
returned as ``{"source", "title", "snippet"}`` records and can never override
system instructions, safety rules, or tool permissions.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_agent.rag.retriever import Retriever

# Default corpus: synthetic SOP documents shipped with the agent (see the
# ``sops/`` sibling directory). Anchored to this file so it works regardless
# of the process working directory.
DEFAULT_CORPUS_DIR = Path(__file__).resolve().parent / "sops"

_WORD_RE = re.compile(r"[A-Za-z0-9]+")

# BM25 parameters (standard values; fully local and deterministic).
_K1 = 1.5
_B = 0.75
_EPS = 1e-9


def _tokenize(text: str) -> List[str]:
    """Lower-case alphanumeric tokens of a text."""
    return [tok.lower() for tok in _WORD_RE.findall(text)]


def _chunk_document(text: str, max_chars: int = 4096) -> List[str]:
    """Split plain text into paragraph chunks, capping each chunk size.

    Paragraph boundaries split short documents into stable chunks. Oversized
    paragraphs are further split on sentence boundaries so a single chunk
    stays within ``max_chars``.
    """
    chunks: List[str] = []
    for paragraph in re.split(r"\n\s*\n|\n", text):
        paragraph = " ".join(paragraph.split())
        if not paragraph:
            continue
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        pieces: List[str] = []
        current = ""
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            if current and len(current) + len(sentence) > max_chars:
                pieces.append(current)
                current = sentence
            else:
                current = (current + " " + sentence).strip()
        if current:
            pieces.append(current)
        chunks.extend(pieces)
    return chunks


def _read_corpus(corpus_dir: Path) -> List[Dict[str, str]]:
    """Load every ``.txt`` file under ``corpus_dir`` into untagged chunks.

    The first line of each file is treated as the document title; the rest of
    the file is the body, chunked by paragraph.
    """
    documents: List[Dict[str, str]] = []
    if not corpus_dir.is_dir():
        return documents
    for path in sorted(corpus_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        lines = text.splitlines()
        title = lines[0].strip() if lines else path.stem
        body = "\n".join(lines[1:]).strip()
        if not body:
            continue
        chunks = _chunk_document(body)
        if not chunks:
            continue
        for chunk in chunks:
            documents.append(
                {"source": path.name, "title": title, "text": chunk}
            )
    return documents


def _idf(term: str, document_frequencies: Dict[str, int], n_documents: int) -> float:
    document_frequency = document_frequencies.get(term, 0)
    return math.log(
        1.0 + (n_documents - document_frequency + 0.5) / (document_frequency + 0.5)
    )


class _Bm25Scorer:
    """Small dependency-free BM25-style scorer over an in-memory corpus."""

    def __init__(self, documents: List[Dict[str, str]]) -> None:
        self._tokenized: List[List[str]] = [
            _tokenize(document["text"]) for document in documents
        ]
        self._document_frequencies: Dict[str, int] = {}
        for tokens in self._tokenized:
            for term in set(tokens):
                self._document_frequencies[term] = (
                    self._document_frequencies.get(term, 0) + 1
                )
        total = sum(len(tokens) for tokens in self._tokenized)
        self._average_length = total / max(1, len(documents))
        self._n_documents = len(documents)

    def score(self, query_terms: List[str], tokens: List[str]) -> float:
        if not query_terms:
            return 0.0
        term_frequencies: Dict[str, int] = {}
        for term in tokens:
            term_frequencies[term] = term_frequencies.get(term, 0) + 1
        document_length = len(tokens)
        score = 0.0
        for term in set(query_terms):
            frequency = term_frequencies.get(term)
            if not frequency:
                continue
            length_norm = 1.0 - _B + _B * (document_length / self._average_length)
            idf = _idf(term, self._document_frequencies, self._n_documents)
            score += idf * (frequency * (_K1 + 1.0)) / (frequency + _K1 * length_norm)
        return score

    def rank(self, query_terms: List[str]) -> List[float]:
        """One BM25 score per corpus document, in corpus order."""
        return [self.score(query_terms, tokens) for tokens in self._tokenized]


class KnowledgeRetriever(Retriever):
    """Local, offline, dependency-free retriever over a plain-text corpus.

    Args:
        corpus_dir: Directory of ``.txt`` knowledge documents to index. Defaults
            to the shipped SOP corpus.
        top_k: Maximum number of retrieved chunks to return.

    Honest retrieval semantics: a chunk is returned only when its BM25 score
    is strictly positive. Queries with no overlap (and an empty query / empty
    corpus) return no results — never fabricated ones.
    """

    def __init__(
        self,
        corpus_dir: str | Path = DEFAULT_CORPUS_DIR,
        top_k: int = 2,
    ) -> None:
        self._corpus_dir = Path(corpus_dir)
        self._top_k = max(1, int(top_k))
        self._documents: List[Dict[str, str]] = []
        self._scorer: Optional[_Bm25Scorer] = None
        self._load()

    def _load(self) -> None:
        self._documents = _read_corpus(self._corpus_dir)
        self._scorer = _Bm25Scorer(self._documents) if self._documents else None

    def retrieve(
        self,
        query: str,
        *,
        permit_id: Optional[str] = None,
        source: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Rank local corpus chunks against ``query``.

        Returns the top-``top_k`` chunks as ``{"source", "title", "snippet"}``
        records. Fixture-provided ``context["knowledge"]`` (when present) is
        appended unchanged for backward compatibility. Empty/no-match queries
        return only that fixture knowledge (usually nothing).
        """
        fixture_knowledge: List[Any] = []
        if context and isinstance(context.get("knowledge"), list):
            fixture_knowledge = list(context["knowledge"])

        if not query or self._scorer is None or not self._documents:
            return fixture_knowledge

        query_terms = _tokenize(query)
        scores = self._scorer.rank(query_terms)
        ranked = sorted(
            zip(self._documents, scores),
            key=lambda pair: pair[1],
            reverse=True,
        )

        retrieved: List[Dict[str, str]] = []
        for document, score in ranked:
            if score <= 0.0 or len(retrieved) >= self._top_k:
                continue
            retrieved.append(
                {
                    "source": document["source"],
                    "title": document["title"],
                    "snippet": document["text"],
                }
            )
        return retrieved + fixture_knowledge


def build_knowledge_retriever(
    corpus_dir: str | Path = DEFAULT_CORPUS_DIR,
    top_k: int = 2,
) -> KnowledgeRetriever:
    """Factory: a real local ``KnowledgeRetriever`` over the default corpus."""
    return KnowledgeRetriever(corpus_dir=corpus_dir, top_k=top_k)