VIDEO_STATUSES = {
    "PENDING",
    "UPLOADING",
    "UPLOADED",
    "QUEUED",
    "PROCESSING",
    "MEDIA_PROCESSED",
    "AI_PROCESSED",
    "INDEXED",
    "ANALYTICS_READY",
    "COMPLETED",
    "FAILED",
    "DELETED",
}

USER_ROLES = {"USER", "ADMIN"}

KNOWN_SERVICES = {
    "media-processor",
    "ai-vision-nlp",
    "search-discovery",
    "video-analytics",
    "agentic-researcher",
}

WORKFLOW_QUEUE_NAME = "media_processing_jobs"
CLEANUP_QUEUE_NAME = "cleanup-jobs"
