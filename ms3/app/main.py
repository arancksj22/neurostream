from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.db import build_repository
from app.services.indexing import IndexingService
from app.services.metadata import MetadataService
from app.services.search import SearchService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    repository = await build_repository(
        database_url=settings.database_url,
        embedding_dimensions=settings.embedding_dimensions,
        allow_in_memory_fallback=settings.allow_in_memory_fallback,
    )
    app.state.settings = settings
    app.state.repository = repository
    app.state.indexing_service = IndexingService(repository=repository, settings=settings)
    app.state.search_service = SearchService(repository=repository, settings=settings)
    app.state.metadata_service = MetadataService(repository=repository)
    yield


app = FastAPI(title="NeuroStream MS3", version="0.1.0", lifespan=lifespan)
app.include_router(router)

