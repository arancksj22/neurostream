import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User, Video, WorkflowStatusLog
from ..queues import publish_processing_job
from ..responses import success_response
from ..schemas import CompleteUploadRequest, InitiateUploadRequest
from ..storage import generate_presigned_put_url, get_object_metadata
from ..utils import generate_object_key

router = APIRouter(prefix="/api/upload", tags=["upload"])
logger = logging.getLogger(__name__)


@router.post("/initiate")
def initiate_upload(
    payload: InitiateUploadRequest,
    current_user: User = Depends(get_current_user),
    _db: Session = Depends(get_db),
):
    object_key = generate_object_key(current_user.id, payload.filename)
    upload_url = generate_presigned_put_url(object_key, payload.contentType, expires=900)

    return success_response(
        {
            "uploadUrl": upload_url,
            "objectKey": object_key,
            "expiresIn": 900,
            "bucket": settings.s3_bucket,
        },
        message="Upload URL generated.",
    )


@router.post("/complete")
def complete_upload(
    payload: CompleteUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        metadata = get_object_metadata(payload.objectKey)
    except ClientError as exc:
        raise HTTPException(
            status_code=404,
            detail="Upload verification failed. Object not found in storage.",
        ) from exc

    file_name = payload.objectKey.split("/")[-1] if "/" in payload.objectKey else payload.objectKey
    content_type = metadata.get("ContentType") or "video/mp4"
    file_size = int(metadata.get("ContentLength") or 0)

    video = Video(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        object_key=payload.objectKey,
        file_name=file_name,
        file_size=file_size,
        content_type=content_type,
        status="UPLOADED",
    )
    db.add(video)
    db.flush()

    db.add(
        WorkflowStatusLog(
            video_id=video.id,
            service_name="user-workflow-service",
            status="UPLOADED",
            message="Video uploaded successfully",
        )
    )

    queued = publish_processing_job(
        {
            "job_id": str(uuid.uuid4()),
            "video_id": str(video.id),
            "user_id": str(current_user.id),
            "s3_raw_path": video.object_key,
            "original_filename": video.file_name,
            "content_type": video.content_type,
            "file_size_bytes": int(video.file_size),
        }
    )

    if queued:
        video.status = "QUEUED"
        db.add(
            WorkflowStatusLog(
                video_id=video.id,
                service_name="user-workflow-service",
                status="QUEUED",
                message="Processing job queued",
            )
        )
        db.commit()

        return success_response(
            {
                "videoId": video.id,
                "status": video.status,
                "message": "Video registered and processing started.",
            },
            message="Upload completed and workflow started.",
            status_code=201,
        )

    logger.warning("Upload completed but queue publish failed for video_id=%s", video.id)

    db.add(
        WorkflowStatusLog(
            video_id=video.id,
            service_name="user-workflow-service",
            status="FAILED",
            message="Processing queue unavailable; retry required",
        )
    )
    db.commit()

    return success_response(
        {
            "videoId": video.id,
            "status": video.status,
            "message": "Upload completed, but processing queue is unavailable.",
        },
        message="Upload completed. Processing did not start because queue is unavailable.",
        status_code=202,
    )
