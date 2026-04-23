from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..constants import VIDEO_STATUSES
from ..database import get_db
from ..deps import get_current_user
from ..ms5_client import forward_event_to_ms5
from ..models import DeletedVideoCleanupLog, User, Video, WorkflowStatusLog
from ..queues import publish_cleanup_job
from ..responses import paginated_response, success_response
from ..schemas import RenameVideoRequest, VideoInteractionEventRequest
from ..serializers import serialize_video, serialize_workflow_log
from ..storage import delete_object, generate_presigned_get_url_cached
from ..utils import utc_now

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("")
def fetch_library(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=50),
    search: str | None = Query(default=None, max_length=120),
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if status and status not in VIDEO_STATUSES:
        raise HTTPException(status_code=422, detail="Validation failed: query.status: Invalid enum value")

    filters = [Video.user_id == current_user.id, Video.deleted_at.is_(None)]
    if status:
        filters.append(Video.status == status)
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Video.title.ilike(pattern),
                Video.description.ilike(pattern),
                Video.file_name.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count(Video.id)).where(*filters)) or 0
    items = db.execute(
        select(Video)
        .where(*filters)
        .order_by(Video.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).scalars().all()

    return paginated_response([serialize_video(item) for item in items], page, limit, int(total))


@router.get("/{video_id}")
def fetch_video_details(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    video = db.scalar(
        select(Video).where(
            Video.id == video_id,
            Video.user_id == current_user.id,
            Video.deleted_at.is_(None),
        )
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    logs = db.execute(
        select(WorkflowStatusLog)
        .where(WorkflowStatusLog.video_id == video.id)
        .order_by(WorkflowStatusLog.created_at.asc())
    ).scalars().all()

    return success_response(
        {
            **serialize_video(video),
            "fileUrl": generate_presigned_get_url_cached(video.object_key),
            "workflowLogs": [serialize_workflow_log(log) for log in logs],
            "searchableReady": video.status in {"INDEXED", "ANALYTICS_READY", "COMPLETED"},
            "processedReady": video.status in {"ANALYTICS_READY", "COMPLETED"},
        }
    )


@router.post("/{video_id}/events")
def ingest_video_event(
    video_id: str,
    payload: VideoInteractionEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    video = db.scalar(
        select(Video).where(
            Video.id == video_id,
            Video.user_id == current_user.id,
            Video.deleted_at.is_(None),
        )
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    forwarded = forward_event_to_ms5(
        user_id=current_user.id,
        video_id=video.id,
        event_type=payload.eventType,
        timestamp_sec=payload.timestampSec,
        query_text=payload.queryText,
        session_id=payload.sessionId,
    )

    if not forwarded:
        raise HTTPException(status_code=502, detail="Failed to forward event to analytics service.")

    return success_response(
        {
            "videoId": video.id,
            "eventType": payload.eventType,
            "forwarded": True,
        },
        message="Video event forwarded to analytics service.",
        status_code=201,
    )


@router.patch("/{video_id}/rename")
def rename_video(
    video_id: str,
    payload: RenameVideoRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    video = db.scalar(
        select(Video).where(
            Video.id == video_id,
            Video.user_id == current_user.id,
            Video.deleted_at.is_(None),
        )
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    video.title = payload.title
    db.add(
        WorkflowStatusLog(
            video_id=video.id,
            service_name="user-workflow-service",
            status=video.status,
            message=f'Video renamed to "{payload.title}"',
        )
    )
    db.commit()
    db.refresh(video)

    return success_response(serialize_video(video), message="Video renamed successfully.")


@router.delete("/{video_id}")
def delete_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    video = db.scalar(
        select(Video).where(
            Video.id == video_id,
            Video.user_id == current_user.id,
            Video.deleted_at.is_(None),
        )
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    storage_deleted = False
    try:
        delete_object(video.object_key)
        storage_deleted = True
    except Exception:
        storage_deleted = False

    video.status = "DELETED"
    video.deleted_at = utc_now()

    db.add(
        WorkflowStatusLog(
            video_id=video.id,
            service_name="user-workflow-service",
            status="DELETED",
            message=(
                "Video deleted and object removed from storage"
                if storage_deleted
                else "Video marked for deletion and cleanup queued"
            ),
        )
    )
    db.add(
        DeletedVideoCleanupLog(
            video_id=video.id,
            object_key=video.object_key,
            status="COMPLETED" if storage_deleted else "PENDING",
            attempts=0 if storage_deleted else 1,
        )
    )
    db.commit()

    if not storage_deleted:
        publish_cleanup_job(
            {
                "videoId": video.id,
                "userId": current_user.id,
                "objectKey": video.object_key,
            }
        )

    return success_response(
        {
            "id": video.id,
            "status": video.status,
            "message": (
                "Video deleted and removed from storage."
                if storage_deleted
                else "Video deleted and downstream cleanup scheduled."
            ),
        },
        message="Video deleted successfully.",
    )
