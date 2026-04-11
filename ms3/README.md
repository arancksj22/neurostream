# NeuroStream MS3

MS3 is the search and discovery service for NeuroStream. It accepts transcript chunks and embeddings from MS2, stores them, and serves search and retrieval endpoints for downstream services.

## Endpoints

- `POST /index` indexes transcript chunks and embeddings for a video.
- `GET /search` runs hybrid search with optional metadata filters.
- `GET /video/{video_id}/status` returns readiness for a video.
- `GET /video/{video_id}/chunks` returns indexed chunks for a video.
- `GET /video/{video_id}/context` returns formatted retrieval blocks for RAG.
- `GET /health` reports service health and storage backend.

## Environment

- `DATABASE_URL`
- `MS4_BASE_URL`
- `EMBEDDING_DIMENSIONS` (default `768`)
- `SEARCH_DEFAULT_LIMIT` (default `5`)
- `SEARCH_MAX_LIMIT` (default `20`)
- `ALLOW_IN_MEMORY_FALLBACK` (default `true`)

If `DATABASE_URL` is not set, the service falls back to an in-memory repository so the API can still be exercised locally.

## Local Run

```bash
uv sync
uvicorn app.main:app --reload
```
