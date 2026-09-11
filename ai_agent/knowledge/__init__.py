"""Minimal local knowledge/retrieval support for the VYOMA agent.

Provides a plain-text corpus retriever (chunked locally, ranked with a
dependency-free BM25-style scorer). No embeddings, no vector store, no
network calls, and no new dependencies: pure standard library.
"""