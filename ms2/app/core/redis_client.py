from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from uuid import UUID

from celery import Celery
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.models.schemas import JobStatusResponse


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(slots=True)
class JobRecord:
    job_id: str
    video_id: UUID | None = None
    status: str = "queued"
    detail: str | None = None
    updated_at: datetime = field(default_factory=_utcnow)
    chunks_generated: int = 0
    ms3_notified: bool = False
    ms4_notified: bool = False
    error: str | None = None

    def to_response(self) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=self.job_id,
            video_id=self.video_id,
            status=self.status,
            detail=self.detail,
            updated_at=self.updated_at,
            chunks_generated=self.chunks_generated,
            ms3_notified=self.ms3_notified,
            ms4_notified=self.ms4_notified,
            error=self.error,
        )


class JobTracker:
    def __init__(self, redis_url: str | None = None) -> None:
        self._records: dict[str, JobRecord] = {}
        self._lock = Lock()
        self._redis = Redis.from_url(redis_url, decode_responses=True) if redis_url else None

    @staticmethod
    def _redis_key(job_id: str) -> str:
        return f"ms2:job:{job_id}"

    def _write_redis(self, record: JobRecord) -> None:
        if self._redis is None:
            return
        payload = {
            "job_id": record.job_id,
            "video_id": str(record.video_id) if record.video_id else None,
            "status": record.status,
            "detail": record.detail,
            "updated_at": record.updated_at.isoformat(),
            "chunks_generated": record.chunks_generated,
            "ms3_notified": record.ms3_notified,
            "ms4_notified": record.ms4_notified,
            "error": record.error,
        }
        try:
            self._redis.set(self._redis_key(record.job_id), json.dumps(payload))
        except RedisError:
            return

    def _read_redis(self, job_id: str) -> JobRecord | None:
        if self._redis is None:
            return None
        try:
            raw_payload = self._redis.get(self._redis_key(job_id))
        except RedisError:
            return None
        if raw_payload is None:
            return None
        payload = json.loads(raw_payload)
        return JobRecord(
            job_id=payload["job_id"],
            video_id=UUID(payload["video_id"]) if payload.get("video_id") else None,
            status=payload.get("status", "queued"),
            detail=payload.get("detail"),
            updated_at=datetime.fromisoformat(payload["updated_at"]),
            chunks_generated=payload.get("chunks_generated", 0),
            ms3_notified=payload.get("ms3_notified", False),
            ms4_notified=payload.get("ms4_notified", False),
            error=payload.get("error"),
        )

    def update(self, job_id: str, **changes) -> JobStatusResponse:
        with self._lock:
            record = self._records.get(job_id) or self._read_redis(job_id) or JobRecord(job_id=job_id)
            for key, value in changes.items():
                setattr(record, key, value)
            record.updated_at = _utcnow()
            self._records[job_id] = record
            self._write_redis(record)
            return record.to_response()

    def get(self, job_id: str) -> JobStatusResponse | None:
        with self._lock:
            record = self._records.get(job_id) or self._read_redis(job_id)
            return None if record is None else record.to_response()


_job_tracker: JobTracker | None = None


def get_job_tracker() -> JobTracker:
    global _job_tracker
    if _job_tracker is None:
        _job_tracker = JobTracker(get_settings().redis_url)
    return _job_tracker


def build_celery_app(redis_url: str | None) -> Celery:
    broker_url = redis_url or "memory://"
    backend_url = redis_url or "cache+memory://"
    celery_app = Celery("neurostream-ms2", broker=broker_url, backend=backend_url)
    celery_app.conf.task_default_queue = "neurostream-ms2"
    celery_app.conf.task_serializer = "json"
    celery_app.conf.result_serializer = "json"
    celery_app.conf.accept_content = ["json"]
    return celery_app
