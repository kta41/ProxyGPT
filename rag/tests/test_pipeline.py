from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from proxygpt_rag.pipeline import RagPipeline, SearchResult


class FakeEmbeddings:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0] for text in texts]


class FakeStore:
    def __init__(self) -> None:
        self.documents: dict[str, list[object]] = {}
        self.deleted_sources: set[str] | None = None

    def replace_document(self, source: str, chunks: list[object]) -> None:
        self.documents[source] = chunks

    def search(self, vector: list[float], limit: int) -> list[SearchResult]:
        if not self.documents:
            return []
        stored = next(iter(self.documents.values()))[0]
        chunk = stored.chunk
        return [
            SearchResult(
                source=chunk.source,
                title=chunk.title,
                heading=chunk.heading,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                score=0.9,
            )
        ][:limit]

    def delete_sources_not_in(self, active_sources: set[str]) -> int:
        self.deleted_sources = set(active_sources)
        removed = set(self.documents) - active_sources
        for source in removed:
            del self.documents[source]
        return len(removed)


class RagPipelineTests(unittest.TestCase):
    def make_pipeline(self, store: FakeStore) -> RagPipeline:
        return RagPipeline(
            FakeEmbeddings(),
            store,
            chunk_size=100,
            chunk_overlap=10,
            embedding_batch_size=2,
        )

    def test_ingests_markdown_and_returns_retrievable_citation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "guide.md").write_text("# Guide\n\nGit is the source of truth.", encoding="utf-8")
            store = FakeStore()
            pipeline = self.make_pipeline(store)

            document_count, chunk_count = pipeline.ingest_directory(root)
            results = pipeline.retrieve("What is the source of truth?", limit=3)

        self.assertEqual(document_count, 1)
        self.assertEqual(chunk_count, 1)
        self.assertEqual(results[0].citation, "guide.md#chunk-0001")

    def test_prune_missing_only_runs_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "kept.md").write_text("Current content", encoding="utf-8")
            store = FakeStore()
            store.documents["removed.md"] = []
            pipeline = self.make_pipeline(store)

            pipeline.ingest_directory(root)
            self.assertIn("removed.md", store.documents)
            pipeline.ingest_directory(root, prune_missing=True)

        self.assertNotIn("removed.md", store.documents)
        self.assertEqual(store.deleted_sources, {"kept.md"})

    def test_empty_directory_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ValueError, "No Markdown files"):
                self.make_pipeline(FakeStore()).ingest_directory(Path(temporary_directory))

    def test_rejects_empty_question(self) -> None:
        with self.assertRaisesRegex(ValueError, "Question must not be empty"):
            self.make_pipeline(FakeStore()).retrieve("  ", limit=5)


if __name__ == "__main__":
    unittest.main()
