from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from proxygpt_rag.documents import chunk_markdown, iter_markdown


class MarkdownChunkingTests(unittest.TestCase):
    def test_keeps_heading_metadata_and_citations_stable(self) -> None:
        markdown = "# Platform\n\nIntro.\n\n## GitOps\n\nArgo CD reconciles Git."
        first = chunk_markdown(
            markdown,
            source="guide.md",
            title="guide",
            max_chars=100,
            overlap=10,
        )
        second = chunk_markdown(
            markdown,
            source="guide.md",
            title="guide",
            max_chars=100,
            overlap=10,
        )

        self.assertEqual([chunk.point_id for chunk in first], [chunk.point_id for chunk in second])
        self.assertEqual(first[0].heading, "Platform")
        self.assertTrue(any(chunk.heading == "Platform > GitOps" for chunk in first))
        self.assertEqual(first[0].citation, "guide.md#chunk-0001")
        self.assertTrue(all(len(chunk.text) <= 100 for chunk in first))

    def test_splits_long_markdown_with_overlap(self) -> None:
        words = [f"word{index}" for index in range(80)]
        markdown = " ".join(words)
        chunks = chunk_markdown(
            markdown,
            source="long.md",
            title="long",
            max_chars=90,
            overlap=20,
        )

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk.text) <= 90 for chunk in chunks))
        self.assertTrue(set(chunks[0].text.split()) & set(chunks[1].text.split()))

    def test_empty_document_has_no_chunks(self) -> None:
        self.assertEqual(
            chunk_markdown(
                " \n\t",
                source="empty.md",
                title="empty",
                max_chars=100,
                overlap=10,
            ),
            [],
        )

    def test_disallows_invalid_chunk_parameters(self) -> None:
        with self.assertRaises(ValueError):
            chunk_markdown("text", source="a.md", title="a", max_chars=0, overlap=0)
        with self.assertRaises(ValueError):
            chunk_markdown("text", source="a.md", title="a", max_chars=10, overlap=10)

    def test_markdown_discovery_skips_hidden_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "visible").mkdir()
            (root / ".private").mkdir()
            (root / "visible" / "guide.md").write_text("Guide", encoding="utf-8")
            (root / ".private" / "secret.md").write_text("Do not ingest", encoding="utf-8")
            (root / "readme.txt").write_text("Not Markdown", encoding="utf-8")

            self.assertEqual(
                iter_markdown(root),
                [(root / "visible" / "guide.md", "visible/guide.md")],
            )


if __name__ == "__main__":
    unittest.main()
