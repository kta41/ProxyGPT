from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from proxygpt_rag.documents import Chunk, chunk_markdown, iter_markdown


@dataclass(frozen=True)
class SearchResult:
    source: str
    title: str
    heading: str
    chunk_index: int
    text: str
    score: float

    @property
    def citation(self) -> str:
        return f"{self.source}#chunk-{self.chunk_index:04d}"


@dataclass(frozen=True)
class StoredChunk:
    chunk: Chunk
    vector: list[float]


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorStore(Protocol):
    def replace_document(self, source: str, chunks: list[StoredChunk]) -> None: ...

    def search(self, vector: list[float], limit: int) -> list[SearchResult]: ...

    def delete_sources_not_in(self, active_sources: set[str]) -> int: ...


class TextGenerator(Protocol):
    def answer(self, question: str, context: list[SearchResult]) -> str: ...


class RagPipeline:
    def __init__(
        self,
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
        *,
        chunk_size: int,
        chunk_overlap: int,
        embedding_batch_size: int,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be between 0 and chunk_size - 1.")
        if embedding_batch_size <= 0:
            raise ValueError("embedding_batch_size must be greater than zero.")

        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_batch_size = embedding_batch_size

    def ingest_directory(self, root: Path, *, prune_missing: bool = False) -> tuple[int, int]:
        documents = iter_markdown(root)
        if not documents:
            raise ValueError(f"No Markdown files found under {root}.")

        active_sources: set[str] = set()
        document_count = 0
        chunk_count = 0

        for path, source in documents:
            markdown = path.read_text(encoding="utf-8")
            chunks = chunk_markdown(
                markdown,
                source=source,
                title=path.stem,
                max_chars=self.chunk_size,
                overlap=self.chunk_overlap,
            )
            if not chunks:
                continue

            vectors: list[list[float]] = []
            for offset in range(0, len(chunks), self.embedding_batch_size):
                batch = chunks[offset : offset + self.embedding_batch_size]
                batch_vectors = self.embedding_client.embed([chunk.text for chunk in batch])
                if len(batch_vectors) != len(batch):
                    raise RuntimeError(
                        f"Embedding service returned {len(batch_vectors)} vectors "
                        f"for {len(batch)} chunks from {source}."
                    )
                vectors.extend(batch_vectors)

            dimensions = {len(vector) for vector in vectors}
            if len(dimensions) != 1 or not dimensions or 0 in dimensions:
                raise RuntimeError(f"Embedding service returned inconsistent vectors for {source}.")
            if any(not all(map(_is_finite, vector)) for vector in vectors):
                raise RuntimeError(f"Embedding service returned non-finite values for {source}.")

            stored = [
                StoredChunk(chunk=chunk, vector=vector)
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
            self.vector_store.replace_document(source, stored)
            active_sources.add(source)
            document_count += 1
            chunk_count += len(stored)

        if document_count == 0:
            raise ValueError(f"No non-empty Markdown documents found under {root}.")

        if prune_missing:
            self.vector_store.delete_sources_not_in(active_sources)

        return document_count, chunk_count

    def retrieve(self, question: str, *, limit: int) -> list[SearchResult]:
        question = question.strip()
        if not question:
            raise ValueError("Question must not be empty.")
        if limit <= 0:
            raise ValueError("limit must be greater than zero.")

        vectors = self.embedding_client.embed([question])
        if len(vectors) != 1 or not vectors[0]:
            raise RuntimeError("Embedding service did not return exactly one query vector.")
        vector = vectors[0]
        if not all(map(_is_finite, vector)):
            raise RuntimeError("Embedding service returned non-finite values for the query.")
        return self.vector_store.search(vector, limit)

    @staticmethod
    def answer(
        question: str,
        context: list[SearchResult],
        generator: TextGenerator,
    ) -> str:
        if not context:
            return "No relevant indexed sources were found; no answer was generated."
        return generator.answer(question.strip(), context)


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
