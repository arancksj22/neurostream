from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


ChunkSource = Literal["audio", "visual"]


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    storage_backend: str


class ChunkInput(BaseModel):
    chunk_index: int = Field(ge=0)
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)
    text: str = Field(min_length=1)
    source: ChunkSource = "audio"
    embedding: list[float] = Field(default_factory=list)
    frame_ref: str | None = None

    @model_validator(mode="after")
    def validate_times(self) -> "ChunkInput":
        if self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        return self


class IndexRequest(BaseModel):
    job_id: str | None = None
    video_id: UUID
    title: str | None = None
    language: str | None = None
    uploaded_at: datetime | None = None
    chunks: list[ChunkInput] = Field(min_length=1)


class IndexResponse(BaseModel):
    video_id: UUID
    status: str
    indexed_chunks: int
    storage_backend: str
    ms4_notified: bool


class SearchResult(BaseModel):
    video_id: UUID
    title: str | None = None
    language: str | None = None
    chunk_id: int
    chunk_index: int
    start_time: float
    end_time: float
    text: str
    source: ChunkSource
    score: float
    frame_ref: str | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    storage_backend: str


class VideoStatusResponse(BaseModel):
    video_id: UUID
    status: str
    indexed_at: datetime | None = None


class ChunkResponse(BaseModel):
    id: int
    video_id: UUID
    chunk_index: int
    start_time: float
    end_time: float
    text: str
    source: ChunkSource
    frame_ref: str | None = None


class ContextResponse(BaseModel):
    video_id: UUID
    context_blocks: list[str]
    storage_backend: str

