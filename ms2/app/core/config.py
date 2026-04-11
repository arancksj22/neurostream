from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    whisper_model: str
    ms3_base_url: str
    ms4_base_url: str
    embedding_dimensions: int
    process_inline: bool
    mock_external_services: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        service_name=os.getenv("MS2_SERVICE_NAME", "neurostream-ms2"),
        redis_url=os.getenv("REDIS_URL", ""),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        s3_bucket_name=os.getenv("S3_BUCKET_NAME", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_vision_model=os.getenv("GEMINI_VISION_MODEL", ""),
        gemini_embedding_model=os.getenv(
            "GEMINI_EMBEDDING_MODEL",
            "models/text-embedding-004",
        ),
        whisper_model=os.getenv("WHISPER_MODEL", "base"),
        ms3_base_url=os.getenv("MS3_BASE_URL", "").rstrip("/"),
        ms4_base_url=os.getenv("MS4_BASE_URL", "").rstrip("/"),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "768")),
        process_inline=_get_bool("MS2_PROCESS_INLINE", True),
        mock_external_services=_get_bool("MOCK_EXTERNAL_SERVICES", True),
    )

