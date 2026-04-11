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
    database_url: str
    ms4_base_url: str
    embedding_dimensions: int
    search_default_limit: int
    search_max_limit: int
    allow_in_memory_fallback: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        service_name=os.getenv("MS3_SERVICE_NAME", "neurostream-ms3"),
        database_url=os.getenv("DATABASE_URL", ""),
        ms4_base_url=os.getenv("MS4_BASE_URL", "").rstrip("/"),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "768")),
        search_default_limit=int(os.getenv("SEARCH_DEFAULT_LIMIT", "5")),
        search_max_limit=int(os.getenv("SEARCH_MAX_LIMIT", "20")),
        allow_in_memory_fallback=_get_bool("ALLOW_IN_MEMORY_FALLBACK", True),
    )

