from .auth import router as auth_router
from .internal import router as internal_router
from .upload import router as upload_router
from .videos import router as videos_router

__all__ = [
    "auth_router",
    "upload_router",
    "videos_router",
    "internal_router",
]
