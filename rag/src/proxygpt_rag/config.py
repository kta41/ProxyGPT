from __future__ import annotations

import os
import re
from dataclasses import dataclass


DEFAULT_EMBEDDING_MODEL = "qwen3-embedding:0.6b"


def _model_collection_suffix(model: str) -> str:
    suffix = re.sub(r"[^a-zA-Z0-9]+", "_", model).strip("_").lower()
    return suffix or "embedding"


@dataclass(frozen=True)
class Settings:
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str | None = None
    ollama_url: str = "http://127.0.0.1:11435"
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    litellm_url: str = "http://127.0.0.1:4000/v1"
    litellm_api_key: str | None = None
    generation_model: str = "qwen3-14b"
    chunk_size: int = 1800
    chunk_overlap: int = 250
    embedding_batch_size: int = 16

    @property
    def collection_name(self) -> str:
        if self.qdrant_collection:
            return self.qdrant_collection
        return f"proxygpt_knowledge_{_model_collection_suffix(self.embedding_model)}"

    @classmethod
    def from_environment(cls) -> Settings:
        settings = cls(
            qdrant_url=os.environ.get("QDRANT_URL", cls.qdrant_url).rstrip("/"),
            qdrant_api_key=os.environ.get("QDRANT_API_KEY") or None,
            qdrant_collection=os.environ.get("QDRANT_COLLECTION") or None,
            ollama_url=os.environ.get("OLLAMA_BASE_URL", cls.ollama_url).rstrip("/"),
            embedding_model=os.environ.get(
                "RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
            ),
            litellm_url=os.environ.get("LITELLM_BASE_URL", cls.litellm_url).rstrip("/"),
            litellm_api_key=os.environ.get("LITELLM_API_KEY") or None,
            generation_model=os.environ.get("RAG_GENERATION_MODEL", cls.generation_model),
            chunk_size=int(os.environ.get("RAG_CHUNK_SIZE", cls.chunk_size)),
            chunk_overlap=int(os.environ.get("RAG_CHUNK_OVERLAP", cls.chunk_overlap)),
            embedding_batch_size=int(
                os.environ.get("RAG_EMBEDDING_BATCH_SIZE", cls.embedding_batch_size)
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("RAG_CHUNK_SIZE must be greater than zero.")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be between 0 and chunk size - 1.")
        if self.embedding_batch_size <= 0:
            raise ValueError("RAG_EMBEDDING_BATCH_SIZE must be greater than zero.")
        if not self.embedding_model.strip():
            raise ValueError("RAG_EMBEDDING_MODEL must not be empty.")
        if not self.generation_model.strip():
            raise ValueError("RAG_GENERATION_MODEL must not be empty.")
