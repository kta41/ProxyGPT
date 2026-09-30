from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from proxygpt_rag.clients import LiteLLMGenerator, OllamaEmbeddings
from proxygpt_rag.pipeline import SearchResult


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class ClientTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_ollama_embedding_posts_batch_and_returns_vectors(self, urlopen: object) -> None:
        urlopen.return_value = FakeResponse({"embeddings": [[0.1, 0.2], [0.3, 0.4]]})
        client = OllamaEmbeddings("http://localhost:11435/", "qwen3-embedding:0.6b")

        vectors = client.embed(["first", "second"])

        self.assertEqual(vectors, [[0.1, 0.2], [0.3, 0.4]])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost:11435/api/embed")
        self.assertEqual(json.loads(request.data), {
            "model": "qwen3-embedding:0.6b",
            "input": ["first", "second"],
        })

    @patch("urllib.request.urlopen")
    def test_ollama_rejects_wrong_vector_count(self, urlopen: object) -> None:
        urlopen.return_value = FakeResponse({"embeddings": [[0.1, 0.2]]})
        with self.assertRaisesRegex(RuntimeError, "invalid embedding response"):
            OllamaEmbeddings("http://localhost:11435", "embed").embed(["one", "two"])

    @patch("urllib.request.urlopen")
    def test_litellm_generation_marks_retrieved_text_as_untrusted(self, urlopen: object) -> None:
        urlopen.return_value = FakeResponse(
            {"choices": [{"message": {"content": "The answer [guide.md#chunk-0001]."}}]}
        )
        generator = LiteLLMGenerator("http://localhost:4000/v1/", "test-key", "qwen3-14b")
        context = [
            SearchResult(
                source="guide.md",
                title="Guide",
                heading="GitOps",
                chunk_index=1,
                text="Treat documents as untrusted data.",
                score=0.9,
            )
        ]

        answer = generator.answer("How?", context)

        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(answer, "The answer [guide.md#chunk-0001].")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertIn("untrusted data", body["messages"][0]["content"])
        self.assertEqual(
            body["messages"][1]["content"],
            json.dumps(
                {
                    "question": "How?",
                    "untrusted_evidence": [
                        {
                            "citation": "guide.md#chunk-0001",
                            "title": "Guide",
                            "heading": "GitOps",
                            "text": "Treat documents as untrusted data.",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
        )

    def test_litellm_requires_api_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "LITELLM_API_KEY is required"):
            LiteLLMGenerator("http://localhost:4000/v1", "", "qwen3-14b")


if __name__ == "__main__":
    unittest.main()
