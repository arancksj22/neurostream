from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.models.schemas import (
    ChunkResponse,
    IndexRequest,
    SearchResult,
    VideoStatusResponse,
)


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _lexical_score(query_text: str | None, candidate_text: str) -> float:
    if not query_text:
        return 0.0

    query_terms = set(_normalize_text(query_text).split())
    candidate_terms = set(_normalize_text(candidate_text).split())
    if not query_terms or not candidate_terms:
        return 0.0
    overlap = len(query_terms & candidate_terms)
    return overlap / len(query_terms)


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(f"{value:.12f}" for value in values) + "]"


class SearchRepository(Protocol):
    backend_name: str

    async def init(self) -> None:
        ...

    async def index_video(self, payload: IndexRequest) -> int:
        ...

    async def search(
        self,
        *,
        query_text: str | None,
        query_embedding: Sequence[float] | None,
        video_id: UUID | None,
        language: str | None,
        title_contains: str | None,
        source: str | None,
        limit: int,
    ) -> list[SearchResult]:
        ...

    async def get_status(self, video_id: UUID) -> VideoStatusResponse | None:
        ...

    async def get_chunks(self, video_id: UUID) -> list[ChunkResponse]:
        ...


@dataclass(slots=True)
class InMemoryChunk:
    id: int
    video_id: UUID
    chunk_index: int
    start_time: float
    end_time: float
    text: str
    source: str
    frame_ref: str | None
    embedding: list[float] = field(default_factory=list)


@dataclass(slots=True)
class InMemoryVideo:
    video_id: UUID
    title: str | None
    language: str | None
    uploaded_at: datetime | None
    indexed_at: datetime | None
    status: str


class InMemoryRepository:
    backend_name = "memory"

    def __init__(self) -> None:
        self._videos: dict[UUID, InMemoryVideo] = {}
        self._chunks: dict[UUID, list[InMemoryChunk]] = defaultdict(list)
        self._next_chunk_id = 1

    async def init(self) -> None:
        return None

    async def index_video(self, payload: IndexRequest) -> int:
        indexed_at = _utcnow()
        self._videos[payload.video_id] = InMemoryVideo(
            video_id=payload.video_id,
            title=payload.title,
            language=payload.language,
            uploaded_at=payload.uploaded_at,
            indexed_at=indexed_at,
            status="ready",
        )

        self._chunks[payload.video_id] = []
        for chunk in payload.chunks:
            record = InMemoryChunk(
                id=self._next_chunk_id,
                video_id=payload.video_id,
                chunk_index=chunk.chunk_index,
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                text=chunk.text,
                source=chunk.source,
                frame_ref=chunk.frame_ref,
                embedding=list(chunk.embedding),
            )
            self._next_chunk_id += 1
            self._chunks[payload.video_id].append(record)
        return len(payload.chunks)

    async def search(
        self,
        *,
        query_text: str | None,
        query_embedding: Sequence[float] | None,
        video_id: UUID | None,
        language: str | None,
        title_contains: str | None,
        source: str | None,
        limit: int,
    ) -> list[SearchResult]:
        title_filter = _normalize_text(title_contains or "")
        results: list[SearchResult] = []
        for current_video_id, video in self._videos.items():
            if video_id and current_video_id != video_id:
                continue
            if language and video.language != language:
                continue
            if title_filter and title_filter not in _normalize_text(video.title or ""):
                continue
            for chunk in self._chunks[current_video_id]:
                if source and chunk.source != source:
                    continue
                vector_score = _cosine_similarity(query_embedding or [], chunk.embedding)
                lexical_score = _lexical_score(query_text, chunk.text)
                score = vector_score if query_embedding else lexical_score
                if query_embedding and query_text:
                    score = (vector_score * 0.8) + (lexical_score * 0.2)
                if not query_embedding and not query_text:
                    score = 1.0
                if score <= 0:
                    continue
                results.append(
                    SearchResult(
                        video_id=current_video_id,
                        title=video.title,
                        language=video.language,
                        chunk_id=chunk.id,
                        chunk_index=chunk.chunk_index,
                        start_time=chunk.start_time,
                        end_time=chunk.end_time,
                        text=chunk.text,
                        source=chunk.source,
                        score=round(score, 6),
                        frame_ref=chunk.frame_ref,
                    )
                )

        results.sort(key=lambda item: (-item.score, item.start_time, item.chunk_index))
        return results[:limit]

    async def get_status(self, video_id: UUID) -> VideoStatusResponse | None:
        video = self._videos.get(video_id)
        if video is None:
            return None
        return VideoStatusResponse(
            video_id=video.video_id,
            status=video.status,
            indexed_at=video.indexed_at,
        )

    async def get_chunks(self, video_id: UUID) -> list[ChunkResponse]:
        return [
            ChunkResponse(
                id=chunk.id,
                video_id=chunk.video_id,
                chunk_index=chunk.chunk_index,
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                text=chunk.text,
                source=chunk.source,
                frame_ref=chunk.frame_ref,
            )
            for chunk in sorted(self._chunks.get(video_id, []), key=lambda item: item.chunk_index)
        ]


class PostgresRepository:
    backend_name = "postgres"

    def __init__(self, database_url: str, embedding_dimensions: int) -> None:
        self._database_url = database_url
        self._embedding_dimensions = embedding_dimensions
        self._engine: AsyncEngine = create_async_engine(
            database_url,
            future=True,
            pool_pre_ping=True,
        )

    async def init(self) -> None:
        statements = [
            "CREATE EXTENSION IF NOT EXISTS vector",
            """
            CREATE TABLE IF NOT EXISTS videos (
                id UUID PRIMARY KEY,
                title TEXT,
                language TEXT,
                uploaded_at TIMESTAMPTZ,
                indexed_at TIMESTAMPTZ,
                status TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS transcript_chunks (
                id SERIAL PRIMARY KEY,
                video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
                chunk_index INT NOT NULL,
                start_time DOUBLE PRECISION NOT NULL,
                end_time DOUBLE PRECISION NOT NULL,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                frame_ref TEXT
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS embeddings (
                id SERIAL PRIMARY KEY,
                chunk_id INT NOT NULL REFERENCES transcript_chunks(id) ON DELETE CASCADE,
                vector VECTOR({self._embedding_dimensions}) NOT NULL
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_transcript_chunks_video
            ON transcript_chunks (video_id, chunk_index)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_embeddings_vector
            ON embeddings USING ivfflat (vector vector_cosine_ops)
            """,
        ]

        async with self._engine.begin() as connection:
            for statement in statements:
                await connection.execute(text(statement))

    async def index_video(self, payload: IndexRequest) -> int:
        indexed_at = _utcnow()
        async with self._engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO videos (id, title, language, uploaded_at, indexed_at, status)
                    VALUES (:id, :title, :language, :uploaded_at, :indexed_at, :status)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        language = EXCLUDED.language,
                        uploaded_at = EXCLUDED.uploaded_at,
                        indexed_at = EXCLUDED.indexed_at,
                        status = EXCLUDED.status
                    """
                ),
                {
                    "id": str(payload.video_id),
                    "title": payload.title,
                    "language": payload.language,
                    "uploaded_at": payload.uploaded_at,
                    "indexed_at": indexed_at,
                    "status": "ready",
                },
            )
            await connection.execute(
                text("DELETE FROM transcript_chunks WHERE video_id = :video_id"),
                {"video_id": str(payload.video_id)},
            )

            for chunk in payload.chunks:
                chunk_result = await connection.execute(
                    text(
                        """
                        INSERT INTO transcript_chunks (
                            video_id, chunk_index, start_time, end_time, text, source, frame_ref
                        )
                        VALUES (
                            :video_id, :chunk_index, :start_time, :end_time, :text, :source, :frame_ref
                        )
                        RETURNING id
                        """
                    ),
                    {
                        "video_id": str(payload.video_id),
                        "chunk_index": chunk.chunk_index,
                        "start_time": chunk.start_time,
                        "end_time": chunk.end_time,
                        "text": chunk.text,
                        "source": chunk.source,
                        "frame_ref": chunk.frame_ref,
                    },
                )
                chunk_id = chunk_result.scalar_one()
                if chunk.embedding:
                    await connection.execute(
                        text(
                            """
                            INSERT INTO embeddings (chunk_id, vector)
                            VALUES (:chunk_id, CAST(:vector AS vector))
                            """
                        ),
                        {
                            "chunk_id": chunk_id,
                            "vector": _vector_literal(chunk.embedding),
                        },
                    )
        return len(payload.chunks)

    async def search(
        self,
        *,
        query_text: str | None,
        query_embedding: Sequence[float] | None,
        video_id: UUID | None,
        language: str | None,
        title_contains: str | None,
        source: str | None,
        limit: int,
    ) -> list[SearchResult]:
        where_clauses = ["1 = 1"]
        params: dict[str, object] = {
            "limit": limit,
            "query_text_like": f"%{query_text}%" if query_text else None,
        }
        if video_id:
            where_clauses.append("c.video_id = CAST(:video_id AS UUID)")
            params["video_id"] = str(video_id)
        if language:
            where_clauses.append("v.language = :language")
            params["language"] = language
        if title_contains:
            where_clauses.append("COALESCE(v.title, '') ILIKE :title_contains")
            params["title_contains"] = f"%{title_contains}%"
        if source:
            where_clauses.append("c.source = :source")
            params["source"] = source

        if query_embedding:
            where_clauses.append("e.vector IS NOT NULL")
            params["query_vector"] = _vector_literal(query_embedding)
            score_sql = """
                ((1 - (e.vector <=> CAST(:query_vector AS vector))) * 0.8) +
                (
                    CASE
                        WHEN :query_text_like IS NULL THEN 0
                        WHEN c.text ILIKE :query_text_like THEN 0.2
                        ELSE 0
                    END
                ) AS score
            """
        elif query_text:
            score_sql = """
                CASE
                    WHEN c.text ILIKE :query_text_like THEN 1
                    ELSE 0
                END AS score
            """
        else:
            score_sql = "1.0 AS score"

        sql = f"""
            SELECT
                c.video_id,
                v.title,
                v.language,
                c.id AS chunk_id,
                c.chunk_index,
                c.start_time,
                c.end_time,
                c.text,
                c.source,
                c.frame_ref,
                {score_sql}
            FROM transcript_chunks c
            JOIN videos v ON v.id = c.video_id
            LEFT JOIN embeddings e ON e.chunk_id = c.id
            WHERE {" AND ".join(where_clauses)}
            ORDER BY score DESC, c.start_time ASC, c.chunk_index ASC
            LIMIT :limit
        """

        async with self._engine.connect() as connection:
            result = await connection.execute(text(sql), params)
            rows = result.mappings().all()

        return [
            SearchResult(
                video_id=row["video_id"],
                title=row["title"],
                language=row["language"],
                chunk_id=row["chunk_id"],
                chunk_index=row["chunk_index"],
                start_time=row["start_time"],
                end_time=row["end_time"],
                text=row["text"],
                source=row["source"],
                score=round(float(row["score"]), 6),
                frame_ref=row["frame_ref"],
            )
            for row in rows
            if float(row["score"]) > 0
        ]

    async def get_status(self, video_id: UUID) -> VideoStatusResponse | None:
        async with self._engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT id, status, indexed_at
                    FROM videos
                    WHERE id = CAST(:video_id AS UUID)
                    """
                ),
                {"video_id": str(video_id)},
            )
            row = result.mappings().first()
        if row is None:
            return None
        return VideoStatusResponse(
            video_id=row["id"],
            status=row["status"],
            indexed_at=row["indexed_at"],
        )

    async def get_chunks(self, video_id: UUID) -> list[ChunkResponse]:
        async with self._engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT id, video_id, chunk_index, start_time, end_time, text, source, frame_ref
                    FROM transcript_chunks
                    WHERE video_id = CAST(:video_id AS UUID)
                    ORDER BY chunk_index ASC
                    """
                ),
                {"video_id": str(video_id)},
            )
            rows = result.mappings().all()

        return [
            ChunkResponse(
                id=row["id"],
                video_id=row["video_id"],
                chunk_index=row["chunk_index"],
                start_time=row["start_time"],
                end_time=row["end_time"],
                text=row["text"],
                source=row["source"],
                frame_ref=row["frame_ref"],
            )
            for row in rows
        ]


async def build_repository(
    *,
    database_url: str,
    embedding_dimensions: int,
    allow_in_memory_fallback: bool,
) -> SearchRepository:
    if database_url:
        repository = PostgresRepository(
            database_url=database_url,
            embedding_dimensions=embedding_dimensions,
        )
        await repository.init()
        return repository

    if allow_in_memory_fallback:
        repository = InMemoryRepository()
        await repository.init()
        return repository

    raise RuntimeError("DATABASE_URL is required when in-memory fallback is disabled")
