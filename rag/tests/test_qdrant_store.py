from __future__ import annotations

import unittest
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient

from proxygpt_rag.clients import QdrantVectorStore
from proxygpt_rag.config import Settings
from proxygpt_rag.documents import Chunk
from proxygpt_rag.pipeline import StoredChunk


class QdrantStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = QdrantClient(":memory:")
        patcher = patch("proxygpt_rag.clients.QdrantClient", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.store = QdrantVectorStore(
            Settings(qdrant_url="http://unused", qdrant_collection="test_knowledge")
        )
        self.addCleanup(self.store.close)

    def test_upserts_document_and_retrieves_source_metadata(self) -> None:
        chunk = self._chunk(1, "Argo CD reconciles Git.")
        self.store.replace_document(
            "guide.md",
            [StoredChunk(chunk, [1.0, 0.0])],
        )

        results = self.store.search([1.0, 0.0], 3)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].citation, "guide.md#chunk-0001")
        self.assertEqual(results[0].text, "Argo CD reconciles Git.")
        self.assertAlmostEqual(results[0].score, 1.0)

    def test_replacing_a_document_removes_stale_chunks(self) -> None:
        first = self._chunk(1, "Current first chunk.")
        stale = self._chunk(2, "Old second chunk.")
        self.store.replace_document(
            "guide.md",
            [
                StoredChunk(first, [1.0, 0.0]),
                StoredChunk(stale, [0.0, 1.0]),
            ],
        )

        self.store.replace_document(
            "guide.md",
            [StoredChunk(first, [1.0, 0.0])],
        )

        point_count = self.client.count(
            collection_name="test_knowledge",
            exact=True,
        ).count
        results = self.store.search([1.0, 0.0], 10)
        self.assertEqual(point_count, 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].text, "Current first chunk.")

    def test_prune_removes_sources_not_in_the_ingest_set(self) -> None:
        retained = self._chunk(1, "Retained source.")
        removed = self._chunk(1, "Removed source.", source="removed.md")
        self.store.replace_document("guide.md", [StoredChunk(retained, [1.0, 0.0])])
        self.store.replace_document("removed.md", [StoredChunk(removed, [0.0, 1.0])])

        deleted_count = self.store.delete_sources_not_in({"guide.md"})

        self.assertEqual(deleted_count, 1)
        results = self.store.search([0.0, 1.0], 10)
        self.assertEqual([result.source for result in results], ["guide.md"])

    @staticmethod
    def _chunk(index: int, text: str, *, source: str = "guide.md") -> Chunk:
        return Chunk(
            point_id=uuid5(NAMESPACE_URL, f"test:{source}:{index}"),
            source=source,
            title=source.removesuffix(".md"),
            heading="Guide",
            chunk_index=index,
            text=text,
            document_sha256="0" * 64,
        )


if __name__ == "__main__":
    unittest.main()
