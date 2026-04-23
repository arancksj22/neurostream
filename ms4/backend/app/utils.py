import re
import uuid
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_object_key(user_id: str, filename: str) -> str:
    unique_id = str(uuid.uuid4())
    ext = Path(filename).suffix
    base_name = Path(filename).stem
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", base_name)[:100]
    return f"uploads/{user_id}/{unique_id}/{sanitized}{ext}"


def big_int_to_str(value: int | None) -> str:
    return str(value or 0)
