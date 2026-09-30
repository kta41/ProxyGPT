from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from qdrant_client.http.exceptions import ApiException

from proxygpt_rag.clients import (
    LiteLLMGenerator,
    OllamaEmbeddings,
    QdrantVectorStore,
    check_http_json,
)
from proxygpt_rag.config import Settings
from proxygpt_rag.pipeline import RagPipeline, SearchResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proxygpt-rag",
        description="Ingest Markdown, retrieve relevant passages, and answer with source citations.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check Qdrant and Ollama connectivity.")
    doctor.add_argument("--check-litellm", action="store_true")

    ingest = subparsers.add_parser("ingest", help="Index Markdown files from a directory.")
    ingest.add_argument("source", type=Path)
    ingest.add_argument(
        "--prune-missing",
        action="store_true",
        help="Delete indexed documents absent from the source directory after a successful ingest.",
    )

    search = subparsers.add_parser("search", help="Retrieve matching passages with citations.")
    search.add_argument("question")
    search.add_argument("--limit", type=int, default=5)

    ask = subparsers.add_parser("ask", help="Answer from retrieved passages using LiteLLM.")
    ask.add_argument("question")
    ask.add_argument("--limit", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = Settings.from_environment()
        if args.command == "doctor":
            return _doctor(settings, check_litellm=args.check_litellm)
        if args.command == "ingest":
            return _ingest(settings, args.source, prune_missing=args.prune_missing)
        if args.command == "search":
            results = _retrieve(settings, args.question, limit=args.limit)
            print(
                json.dumps(
                    [_result_to_json(result) for result in results],
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.command == "ask":
            results = _retrieve(settings, args.question, limit=args.limit)
            if not results:
                print("No relevant indexed sources were found; no answer was generated.")
                return 0
            generator = LiteLLMGenerator(
                settings.litellm_url,
                settings.litellm_api_key or "",
                settings.generation_model,
            )
            print(RagPipeline.answer(args.question, results, generator))
            print("\nSources:")
            for result in results:
                print(f"- [{result.citation}] {result.title} — {result.heading} (score={result.score:.4f})")
            return 0
        raise AssertionError(f"Unhandled command: {args.command}")
    except (ApiException, OSError, RuntimeError, ValueError, urllib.error.URLError) as exc:
        print(f"proxygpt-rag: {exc}", file=sys.stderr)
        return 1


def _doctor(settings: Settings, *, check_litellm: bool) -> int:
    qdrant_headers = (
        {"api-key": settings.qdrant_api_key}
        if settings.qdrant_api_key
        else None
    )
    qdrant = check_http_json(f"{settings.qdrant_url}/", headers=qdrant_headers)
    print(f"Qdrant reachable: {qdrant.get('title', 'ok')}")

    tags = check_http_json(f"{settings.ollama_url}/api/tags")
    models = tags.get("models")
    if not isinstance(models, list):
        raise RuntimeError("Ollama returned an invalid model list.")
    available = {item.get("name") for item in models if isinstance(item, dict)}
    if settings.embedding_model not in available:
        raise RuntimeError(
            f"Ollama is reachable, but embedding model {settings.embedding_model!r} "
            "is not installed. Pull it before ingesting."
        )
    print(f"Ollama reachable; embedding model available: {settings.embedding_model}")

    if check_litellm:
        if not settings.litellm_api_key:
            raise ValueError("LITELLM_API_KEY is required with --check-litellm.")
        # LiteLLM exposes this OpenAI-compatible endpoint for model discovery.
        request = urllib.request.Request(
            f"{settings.litellm_url}/models",
            headers={"Authorization": f"Bearer {settings.litellm_api_key}"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise RuntimeError("LiteLLM returned an invalid model list.")
        print(f"LiteLLM reachable; {len(payload['data'])} model(s) available.")
    return 0


def _ingest(settings: Settings, source: Path, *, prune_missing: bool) -> int:
    store = QdrantVectorStore(settings)
    try:
        document_count, chunk_count = _pipeline(settings, store=store).ingest_directory(
            source,
            prune_missing=prune_missing,
        )
    finally:
        store.close()
    print(
        f"Indexed {document_count} Markdown document(s), {chunk_count} chunk(s) "
        f"into collection {settings.collection_name!r}."
    )
    if prune_missing:
        print("Removed indexed sources absent from the supplied source directory.")
    return 0


def _pipeline(settings: Settings, *, store: QdrantVectorStore | None = None) -> RagPipeline:
    if store is None:
        store = QdrantVectorStore(settings)
    return RagPipeline(
        OllamaEmbeddings(settings.ollama_url, settings.embedding_model),
        store,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        embedding_batch_size=settings.embedding_batch_size,
    )


def _retrieve(settings: Settings, question: str, *, limit: int) -> list[SearchResult]:
    store = QdrantVectorStore(settings)
    try:
        return _pipeline(settings, store=store).retrieve(question, limit=limit)
    finally:
        store.close()


def _result_to_json(result: SearchResult) -> dict[str, object]:
    return {
        "citation": result.citation,
        "source": result.source,
        "title": result.title,
        "heading": result.heading,
        "chunk_index": result.chunk_index,
        "score": result.score,
        "text": result.text,
    }


if __name__ == "__main__":
    raise SystemExit(main())
