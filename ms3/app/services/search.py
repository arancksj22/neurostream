from __future__ import annotations

from typing import Sequence
from uuid import UUID

from app.core.config import Settings
from app.core.db import SearchRepository
from app.models.schemas import SearchResponse


class SearchService:
    def __init__(self, repository: SearchRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    async def search(
        self,
        *,
        query_text: str | None,
        query_embedding: Sequence[float] | None,
        video_id: UUID | None,
        language: str | None,
        title_contains: str | None,
        source: str | None,
        limit: int | None,
    ) -> SearchResponse:
        resolved_limit = min(
            limit or self._settings.search_default_limit,
            self._settings.search_max_limit,
        )
        if query_embedding and len(query_embedding) != self._settings.embedding_dimensions:
            raise ValueError(
                "query embedding length does not match EMBEDDING_DIMENSIONS "
                f"({self._settings.embedding_dimensions})"
            )

        results = await self._repository.search(
            query_text=query_text,
            query_embedding=query_embedding,
            video_id=video_id,
            language=language,
            title_contains=title_contains,
            source=source,
            limit=resolved_limit,
        )
        return SearchResponse(
            results=results,
            total=len(results),
            storage_backend=self._repository.backend_name,
        )

