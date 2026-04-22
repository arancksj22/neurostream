from __future__ import annotations

from typing import Annotated
from uuid import UUID

import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.models.schemas import ContextResponse, HealthResponse, IndexRequest, IndexResponse, SearchResponse
from app.services.indexing import IndexingService
from app.services.metadata import MetadataService
from app.services.search import SearchService


router = APIRouter()


def get_indexing_service(request: Request) -> IndexingService:
    return request.app.state.indexing_service


def get_search_service(request: Request) -> SearchService:
    return request.app.state.search_service


def get_metadata_service(request: Request) -> MetadataService:
    return request.app.state.metadata_service


async def _resolve_embedding(
    request: Request,
    query_text: str | None,
    query_embedding_str: str | None
) -> list[float] | None:
    if query_embedding_str:
        try:
            return [float(part.strip()) for part in query_embedding_str.split(",") if part.strip()]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="query_embedding must be comma-separated floats") from exc

    if not query_text:
        return None

    settings = request.app.state.settings
    if not settings.gemini_api_key:
        return None

    from google import genai
    from google.genai import types
    import math

    client = genai.Client(api_key=settings.gemini_api_key)
    try:
        response = await asyncio.to_thread(
            client.models.embed_content,
            model=settings.gemini_embedding_model,
            contents=[query_text],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=settings.embedding_dimensions,
            ),
        )
        embeddings = getattr(response, "embeddings", None) or []
        vec = embeddings[0].values if embeddings else None

        if vec:
            values = [float(v) for v in vec]
            norm = math.sqrt(sum(v * v for v in values))
            if norm > 0:
                return [v / norm for v in values]
            return values
    except Exception as exc:
        logging.getLogger(__name__).warning("Failed to generate query embedding: %s", exc)

    return None


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    return HealthResponse(
        service=request.app.state.settings.service_name,
        storage_backend=request.app.state.repository.backend_name,
    )


@router.post("/index", response_model=IndexResponse)
async def index_video(
    payload: IndexRequest,
    indexing_service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> IndexResponse:
    try:
        return await indexing_service.index_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/search", response_model=SearchResponse)
async def search(
    request: Request,
    search_service: Annotated[SearchService, Depends(get_search_service)],
    query: str | None = Query(default=None, description="Free-text query"),
    query_embedding: str | None = Query(default=None, description="Comma-separated embedding vector"),
    video_id: UUID | None = None,
    language: str | None = None,
    title_contains: str | None = None,
    source: str | None = Query(default=None, pattern="^(audio|visual)$"),
    limit: int | None = Query(default=None, ge=1),
) -> SearchResponse:
    try:
        resolved_embedding = await _resolve_embedding(request, query, query_embedding)
        return await search_service.search(
            query_text=query,
            query_embedding=resolved_embedding,
            video_id=video_id,
            language=language,
            title_contains=title_contains,
            source=source,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/video/{video_id}/status")
async def video_status(
    video_id: UUID,
    metadata_service: Annotated[MetadataService, Depends(get_metadata_service)],
):
    payload = await metadata_service.get_status(video_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="video not found")
    return payload


@router.get("/video/{video_id}/chunks")
async def video_chunks(
    video_id: UUID,
    metadata_service: Annotated[MetadataService, Depends(get_metadata_service)],
    source: str | None = Query(default=None, pattern="^(audio|visual)$"),
):
    chunks = await metadata_service.get_chunks(video_id, source)
    if not chunks:
        raise HTTPException(status_code=404, detail="video not found")
    return chunks


@router.get("/video/{video_id}/context", response_model=ContextResponse)
async def video_context(
    request: Request,
    video_id: UUID,
    metadata_service: Annotated[MetadataService, Depends(get_metadata_service)],
    query: str | None = None,
    query_embedding: str | None = Query(default=None, description="Comma-separated embedding vector"),
    limit: int = Query(default=5, ge=1),
    source: str | None = Query(default=None, pattern="^(audio|visual)$"),
) -> ContextResponse:
    try:
        resolved_embedding = await _resolve_embedding(request, query, query_embedding)
        payload = await metadata_service.build_context(
            video_id=video_id,
            query_text=query,
            query_embedding=resolved_embedding,
            limit=limit,
            source=source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not payload.context_blocks:
        raise HTTPException(status_code=404, detail="video not found or no matching context")
    return payload
