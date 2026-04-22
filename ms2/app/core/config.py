from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_first_env(names: list[str], default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return default


@dataclass(slots=True)
class Settings:
    service_name: str
    redis_url: str
    aws_access_key_id: str
    aws_secret_access_key: str
    s3_bucket_name: str
    gemini_api_key: str
    gemini_vision_model: str
    gemini_embedding_model: str
    openai_api_key: str
    whisper_model: str
    openai_transcription_requests_per_minute: int
    openai_transcription_segments_per_request: int
    ms3_base_url: str
    ms4_base_url: str
    embedding_dimensions: int
    process_inline: bool
    mock_external_services: bool
    ms4_api_key: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        service_name=os.getenv("MS2_SERVICE_NAME", "neurostream-ms2"),
        redis_url=os.getenv("REDIS_URL", ""),
        aws_access_key_id=_get_first_env(["AWS_ACCESS_KEY_ID", "S3_ACCESS_KEY_ID"], ""),
        aws_secret_access_key=_get_first_env(["AWS_SECRET_ACCESS_KEY", "S3_SECRET_ACCESS_KEY"], ""),
        s3_bucket_name=_get_first_env(["S3_BUCKET_NAME", "AWS_S3_BUCKET"], ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_vision_model=os.getenv("GEMINI_VISION_MODEL", ""),
        gemini_embedding_model=os.getenv(
            "GEMINI_EMBEDDING_MODEL",
            "gemini-embedding-001",
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        whisper_model=os.getenv("WHISPER_MODEL", "whisper-1"),
        openai_transcription_requests_per_minute=int(os.getenv("OPENAI_TRANSCRIPTION_REQUESTS_PER_MINUTE", "8")),
        openai_transcription_segments_per_request=int(os.getenv("OPENAI_TRANSCRIPTION_SEGMENTS_PER_REQUEST", "2")),
        ms3_base_url=os.getenv("MS3_BASE_URL", "").rstrip("/"),
        ms4_base_url=os.getenv("MS4_BASE_URL", "").rstrip("/"),
        ms4_api_key=_get_first_env(["MS4_INTERNAL_API_KEY", "MS4_API_KEY", "MS4_TOKEN", "INTERNAL_API_KEY"], ""),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "768")),
        process_inline=_get_bool("MS2_PROCESS_INLINE", True),
        mock_external_services=_get_bool("MOCK_EXTERNAL_SERVICES", True),
    )
