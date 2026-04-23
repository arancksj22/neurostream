# NeuroStream

A high-performance polyglot microservices platform that transforms raw video uploads into searchable, conversational intelligence. Each service is independently deployable and communicates over HTTP REST and a Redis queue.

---

## Services

| ID  | Name                  | Stack          | Role                                                                 |
|-----|-----------------------|----------------|----------------------------------------------------------------------|
| MS1 | Media Processor       | Go             | Consumes videos from S3, runs FFmpeg for chunking and frame sampling |
| MS2 | AI Perception         | Python/FastAPI | Generates timestamped transcripts and visual embeddings via Gemini   |
| MS3 | Search and Indexing   | Python/FastAPI | Indexes embeddings, serves vector similarity search and RAG context  |
| MS4 | User and Workflow API | Node.js        | Auth, presigned S3 uploads, video metadata, billing, job dispatch    |
| MS5 | Analytics             | Node.js        | Tracks per-user behavior, search patterns, and revisited segments    |
| MS6 | Agentic Brain         | Java/Spring    | Multi-agent LLM pipeline for Q&A, summarization, and research       |
| MS7 | PDF Export            | Python/FastAPI | Converts MS6 outputs into PDFs and uploads them to S3               |

---

## How It Works

1. A user uploads a video through MS4, which writes metadata to PostgreSQL and pushes a processing job to Redis.
2. MS1 picks up the job, downloads the video from S3, and runs FFmpeg to extract audio and sample frames.
3. MS2 transcribes the audio (multi-lingual) and analyzes frames using Gemini Vision to produce text and vector embeddings.
4. MS3 indexes everything into a vector store, making content searchable at low latency.
5. MS5 passively tracks user interactions to surface behavioral analytics and smart highlights.
6. MS6 runs an agentic pipeline on top of MS3's index: Retriever pulls context, Analyzer extracts facts, Synthesizer composes answers, CitationLinker maps claims to timestamps. The Research pipeline adds a Planner agent for iterative multi-query retrieval.
7. After every MS6 response, an async fire-and-forget call to MS7 generates a PDF report and returns a presigned S3 download URL.

---

## Data Layer

| Store      | Purpose                                       |
|------------|-----------------------------------------------|
| PostgreSQL | User accounts, video metadata, billing, jobs  |
| Redis      | Async job queue between MS4, MS1, MS2, MS3    |
| AWS S3     | Raw video storage and exported PDF delivery   |

---

## Local Development

Each service has its own README with setup instructions. For a full stack run:

```bash
docker compose up
```

The `docker-compose.yml` at the root starts all services, PostgreSQL, and Redis with environment variables pre-wired.

---

## Project

Built as part of the MSA coursework project by B048, B053, B056, B057.
