from __future__ import annotations

import asyncio
import hashlib
import logging
import math
from typing import Sequence

from app.core.config import Settings


logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def embed_documents(self, documents: Sequence[str]) -> list[list[float]]:
        if not documents:
            return []

        if not self._settings.mock_external_services and self._settings.gemini_api_key:
            try:
                return await asyncio.to_thread(self._embed_with_gemini, documents)
            except Exception as exc:
                logger.warning("Gemini embeddings failed, falling back to deterministic vectors: %s", exc)

        return [self._deterministic_embedding(document) for document in documents]

    def _embed_with_gemini(self, documents: Sequence[str]) -> list[list[float]]:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._settings.gemini_api_key)
        response = client.models.embed_content(
            model=self._settings.gemini_embedding_model,
            contents=list(documents),
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=self._settings.embedding_dimensions,
            ),
        )

        normalized: list[list[float]] = []
        for embedding in response.embeddings or []:
            values = getattr(embedding, "values", None)
            if values is None:
                continue
            normalized.append(self._normalize([float(value) for value in values]))

        if len(normalized) != len(documents):
            raise RuntimeError("Gemini embedding response did not match document count")
        return normalized

    def _deterministic_embedding(self, document: str) -> list[float]:
        values: list[float] = []
        salt = 0
        while len(values) < self._settings.embedding_dimensions:
            digest = hashlib.sha256(f"{salt}:{document}".encode("utf-8")).digest()
            values.extend(((byte / 255.0) * 2.0) - 1.0 for byte in digest)
            salt += 1
        return self._normalize(values[: self._settings.embedding_dimensions])

    @staticmethod
    def _normalize(values: Sequence[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            return [0.0 for _ in values]
        return [float(value / norm) for value in values]
