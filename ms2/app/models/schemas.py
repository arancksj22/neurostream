from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class AudioSegmentInput(BaseModel):
    s3_key: str = Field(min_length=1)
    start_time: float | None = Field(default=None, ge=0)
    end_time: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_times(self) -> "AudioSegmentInput":
        if self.start_time is not None and self.end_time is not None and self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        return self


class FrameInput(BaseModel):
    s3_key: str = Field(min_length=1)
    timestamp: float | None = Field(default=None, ge=0)


class ProcessRequest(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: UUID
    title: str | None = None
    language: str | None = None
    uploaded_at: datetime | None = None
    audio_segments: list[AudioSegmentInput] = Field(default_factory=list)
    frame_images: list[FrameInput] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_inputs(self) -> "ProcessRequest":
        if not self.audio_segments and not self.frame_images:
            raise ValueError("At least one audio segment or frame image is required")
        return self


class TranscriptSegment(BaseModel):
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)
    text: str = Field(min_length=1)
    source_key: str

    @model_validator(mode="after")
    def validate_times(self) -> "TranscriptSegment":
        if self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        return self


class FrameAnalysis(BaseModel):
    timestamp: float = Field(ge=0)
    description: str = Field(min_length=1)
    source_key: str
    objects: list[str] = Field(default_factory=list)
    onscreen_text: str | None = None


class ProcessResponse(BaseModel):
    job_id: str
    video_id: UUID
    status: str
    chunks_generated: int
    ms3_notified: bool
    ms4_notified: bool
    queued: bool = False


class JobStatusResponse(BaseModel):
    job_id: str
    video_id: UUID | None = None
    status: str
    detail: str | None = None
    updated_at: datetime
    chunks_generated: int = 0
    ms3_notified: bool = False
    ms4_notified: bool = False
    error: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    execution_mode: str

