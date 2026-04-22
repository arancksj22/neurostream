# NeuroStream MS2

MS2 is the AI perception service for NeuroStream. It turns audio and frame references into timestamped transcript chunks, visual descriptions, and embeddings, then forwards the normalized payload to MS3.

## Default local port

- `http://localhost:8002` (Docker Compose host mapping to container port `8000`)

## Endpoints

- `GET /health`
	- Task: Liveness/health check.
	- Also reports whether MS2 is running in `inline` mode or `celery` mode.

- `POST /process`
	- Task: Accept a processing request and run the AI pipeline.
	- In `MS2_PROCESS_INLINE=true`, runs immediately in the API process.
	- In `MS2_PROCESS_INLINE=false`, enqueues work to Celery (Redis broker) and returns a queued response.
	- Expected outcome: MS2 generates transcript/vision chunks + embeddings and notifies MS3 for indexing.

- `GET /status/{job_id}`
	- Task: Return the latest tracked status for a job (queued/running/complete/failed) as seen by MS2.
	- Note: this is a lightweight in-memory tracker for local/dev UX.

## Environment

- `REDIS_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME`
- `GEMINI_API_KEY`
- `GEMINI_VISION_MODEL`
- `GEMINI_EMBEDDING_MODEL`
- `OPENAI_API_KEY`
- `WHISPER_MODEL`
- `MS3_BASE_URL`
- `MS4_BASE_URL`
- `EMBEDDING_DIMENSIONS` (default `768`)
- `MS2_PROCESS_INLINE` (default `true`)
- `MOCK_EXTERNAL_SERVICES` (default `true`)

By default the service uses deterministic fallback implementations so the pipeline can be exercised without live Whisper or Gemini access. Set `MOCK_EXTERNAL_SERVICES=false` once the real model dependencies and credentials are ready.

For production-style deployments, MS2 should run with:

- `MOCK_EXTERNAL_SERVICES=false`
- `OPENAI_API_KEY` set for Whisper transcription
- `GEMINI_API_KEY` set for embeddings and, if enabled, vision analysis
- `GEMINI_EMBEDDING_MODEL=gemini-embedding-001`

## Local Run

```bash
uv sync
uvicorn app.main:app --reload
```
