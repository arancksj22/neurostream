from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.redis_client import build_celery_app, get_job_tracker
from app.models.schemas import ProcessRequest
from app.services.pipeline import build_processing_service


settings = get_settings()
celery_app = build_celery_app(settings.redis_url)
job_tracker = get_job_tracker()


@celery_app.task(name="app.process_media_job")
def process_media_job(payload: dict):
    request = ProcessRequest(**payload)
    job_tracker.update(
        request.job_id,
        video_id=request.video_id,
        status="queued",
        detail="Job claimed by Celery worker",
    )
    try:
        response = asyncio.run(build_processing_service(settings).process(request))
        return response.model_dump()
    except Exception as exc:
        job_tracker.update(
            request.job_id,
            video_id=request.video_id,
            status="failed",
            detail="Background processing failed",
            error=str(exc),
        )
        raise

