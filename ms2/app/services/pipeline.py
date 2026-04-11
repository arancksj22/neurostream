from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.redis_client import JobTracker, get_job_tracker
from app.models.schemas import ProcessRequest, ProcessResponse
from app.services.embeddings import EmbeddingService
from app.services.transcription import TranscriptionService
from app.services.vision import VisionService


logger = logging.getLogger(__name__)


class ProcessingService:
    def __init__(
        self,
        *,
        settings: Settings,
        job_tracker: JobTracker,
        transcription_service: TranscriptionService,
        vision_service: VisionService,
        embedding_service: EmbeddingService,
    ) -> None:
        self._settings = settings
        self._job_tracker = job_tracker
        self._transcription_service = transcription_service
        self._vision_service = vision_service
        self._embedding_service = embedding_service

    async def process(self, payload: ProcessRequest) -> ProcessResponse:
        self._job_tracker.update(
            payload.job_id,
            video_id=payload.video_id,
            status="processing",
            detail="Running transcription",
        )

        transcripts = await self._transcription_service.transcribe(payload.audio_segments)
        self._job_tracker.update(payload.job_id, detail="Running vision analysis")

        frame_analyses = await self._vision_service.analyze(payload.frame_images)

        chunks: list[dict[str, Any]] = [
            {
                "chunk_index": 0,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "text": segment.text,
                "source": "audio",
                "frame_ref": None,
            }
            for segment in transcripts
        ]
        chunks.extend(
            {
                "chunk_index": 0,
                "start_time": analysis.timestamp,
                "end_time": analysis.timestamp,
                "text": analysis.description,
                "source": "visual",
                "frame_ref": analysis.source_key,
            }
            for analysis in frame_analyses
        )

        chunks.sort(key=lambda item: (item["start_time"], item["source"]))
        embeddings = await self._embedding_service.embed_documents([chunk["text"] for chunk in chunks])
        for index, chunk in enumerate(chunks):
            chunk["chunk_index"] = index
            chunk["embedding"] = embeddings[index]

        self._job_tracker.update(
            payload.job_id,
            detail="Forwarding AI perception payload to MS3",
            chunks_generated=len(chunks),
        )

        ms3_notified = await self._notify_ms3(payload=payload, chunks=chunks)
        should_notify_ms4 = ms3_notified or not self._settings.ms3_base_url
        ms4_notified = await self._notify_ms4(payload=payload) if should_notify_ms4 else False
        final_status = "completed" if ms3_notified or not self._settings.ms3_base_url else "partial"

        self._job_tracker.update(
            payload.job_id,
            status=final_status,
            detail="Pipeline finished",
            chunks_generated=len(chunks),
            ms3_notified=ms3_notified,
            ms4_notified=ms4_notified,
        )
        return ProcessResponse(
            job_id=payload.job_id,
            video_id=payload.video_id,
            status=final_status,
            chunks_generated=len(chunks),
            ms3_notified=ms3_notified,
            ms4_notified=ms4_notified,
        )

    async def _notify_ms3(self, *, payload: ProcessRequest, chunks: list[dict[str, Any]]) -> bool:
        if not self._settings.ms3_base_url:
            return False

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self._settings.ms3_base_url}/index",
                    json={
                        "job_id": payload.job_id,
                        "video_id": str(payload.video_id),
                        "title": payload.title,
                        "language": payload.language,
                        "uploaded_at": payload.uploaded_at.isoformat() if payload.uploaded_at else None,
                        "chunks": chunks,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("MS3 callback failed for job %s: %s", payload.job_id, exc)
            return False
        return True

    async def _notify_ms4(self, *, payload: ProcessRequest) -> bool:
        if not self._settings.ms4_base_url:
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.patch(
                    f"{self._settings.ms4_base_url}/jobs/{payload.job_id}/status",
                    json={
                        "status": "ai_complete",
                        "video_id": str(payload.video_id),
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("MS4 status callback failed for job %s: %s", payload.job_id, exc)
            return False
        return True


def build_processing_service(settings: Settings | None = None) -> ProcessingService:
    resolved_settings = settings or get_settings()
    return ProcessingService(
        settings=resolved_settings,
        job_tracker=get_job_tracker(),
        transcription_service=TranscriptionService(resolved_settings),
        vision_service=VisionService(resolved_settings),
        embedding_service=EmbeddingService(resolved_settings),
    )
