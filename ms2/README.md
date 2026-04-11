# NeuroStream MS2

MS2 is the AI perception service for NeuroStream. It turns audio and frame references into timestamped transcript chunks, visual descriptions, and embeddings, then forwards the normalized payload to MS3.

## Endpoints

- `POST /process` starts the AI pipeline inline or via Celery.
- `GET /status/{job_id}` returns the latest job status.
- `GET /health` reports service health and execution mode.

## Environment

- `REDIS_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME`
- `GEMINI_API_KEY`
- `GEMINI_VISION_MODEL`
- `GEMINI_EMBEDDING_MODEL`
- `WHISPER_MODEL`
- `MS3_BASE_URL`
- `MS4_BASE_URL`
- `EMBEDDING_DIMENSIONS` (default `768`)
- `MS2_PROCESS_INLINE` (default `true`)
- `MOCK_EXTERNAL_SERVICES` (default `true`)

By default the service uses deterministic fallback implementations so the pipeline can be exercised without live Whisper or Gemini access. Set `MOCK_EXTERNAL_SERVICES=false` once the real model dependencies and credentials are ready.

## Local Run

```bash
uv sync
uvicorn app.main:app --reload
```
