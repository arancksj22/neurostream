import json
import urllib.request
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import VIDEO_STATUSES
from ..database import get_db
from ..deps import verify_internal_api_key
from ..config import settings
from ..models import CallbackEvent, Video, WorkflowStatusLog
from ..responses import success_response
from ..schemas import StatusCallbackRequest
from ..utils import utc_now

router = APIRouter(prefix="/internal", tags=["internal"])


@router.patch("/job-status", dependencies=[Depends(verify_internal_api_key)])
def update_status(
    payload: StatusCallbackRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if payload.newStatus not in VIDEO_STATUSES:
        raise HTTPException(status_code=422, detail="Validation failed: body.newStatus: Invalid enum value")

    video = db.scalar(select(Video).where(Video.id == payload.videoId, Video.deleted_at.is_(None)))
    if not video:
        raise HTTPException(status_code=404, detail="Video not found or already deleted.")

    video.status = payload.newStatus
    video.updated_at = utc_now()

    db.add(
        CallbackEvent(
            video_id=video.id,
            service_name=payload.serviceName,
            event_type=payload.newStatus,
            payload=payload.metadata,
        )
    )

    db.add(
        WorkflowStatusLog(
            video_id=video.id,
            service_name=payload.serviceName,
            status=payload.newStatus,
            message=payload.message,
        )
    )

    db.commit()

    if payload.newStatus == "MEDIA_PROCESSED" and payload.metadata:
        background_tasks.add_task(trigger_ms2_processing, video, payload.metadata)

    return success_response(
        {
            "videoId": video.id,
            "status": video.status,
            "acknowledged": True,
        },
        message="Callback acknowledged.",
    )


def trigger_ms2_processing(video, metadata):
    try:
        artifacts = metadata.get("artifacts", {})
        chunks = artifacts.get("chunks", [])

        audio_segments = [
            {"s3_key": c["audio_s3_key"], "start_time": c["start_time_seconds"], "end_time": c["end_time_seconds"]}
            for c in chunks
        ]

        frame_images = []
        for c in chunks:
            frames = c.get("frame_s3_keys", [])
            for frame in frames:
                frame_images.append({"s3_key": frame, "timestamp": c["start_time_seconds"]})

        ms2_payload = {
            "job_id": metadata.get("job_id"),
            "video_id": str(video.id),
            "title": video.title,
            "audio_segments": audio_segments,
            "frame_images": frame_images
        }

        req = urllib.request.Request(
            f"{settings.ms2_base_url}/api/v1/process" if "/api" in settings.ms2_base_url else f"{settings.ms2_base_url}/process",
            data=json.dumps(ms2_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Failed to trigger MS2: {e}")
