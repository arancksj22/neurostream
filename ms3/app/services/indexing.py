from __future__ import annotations

import logging

import httpx

from app.core.config import Settings
from app.core.db import SearchRepository
from app.models.schemas import IndexRequest, IndexResponse


logger = logging.getLogger(__name__)


class IndexingService:
    def __init__(self, repository: SearchRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    async def index_payload(self, payload: IndexRequest) -> IndexResponse:
        for chunk in payload.chunks:
            if chunk.embedding and len(chunk.embedding) != self._settings.embedding_dimensions:
                raise ValueError(
                    "chunk embedding length does not match EMBEDDING_DIMENSIONS "
                    f"({self._settings.embedding_dimensions})"
                )

        indexed_chunks = await self._repository.index_video(payload)
        ms4_notified = await self._notify_ms4(video_id=str(payload.video_id))
        return IndexResponse(
            video_id=payload.video_id,
            status="ready",
            indexed_chunks=indexed_chunks,
            storage_backend=self._repository.backend_name,
            ms4_notified=ms4_notified,
        )

    async def _notify_ms4(self, video_id: str) -> bool:
        if not self._settings.ms4_base_url:
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.patch(
                    f"{self._settings.ms4_base_url}/videos/{video_id}/status",
                    json={"status": "ready"},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("MS4 readiness callback failed for video %s: %s", video_id, exc)
            return False
        return True

