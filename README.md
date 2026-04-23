# NeuroStream

NeuroStream is a high-performance polyglot microservices platform designed to transform raw video uploads into searchable conversational intelligence by leveraging specialized processing engines. The architecture utilizes a Node.js orchestrator (MS4) to manage user workflows, billing, and secure S3 uploads, while a Go-based media processor (MS1) handles high-concurrency video chunking and frame extraction. Intelligence is generated through a Python AI pipeline (MS2) that creates multi-lingual transcripts and visual embeddings, which are then indexed by a FastAPI service (MS3) for sub-second vector search. Finally, the platform provides advanced value through a Node.js analytics engine (MS5) that tracks per-user behavioral insights and an Agentic Researcher (MS6) that enables complex RAG-based conversational synthesis over indexed content, all supported by a robust data layer featuring PostgreSQL for relational integrity, Redis for asynchronous coordination, and AWS S3 for object storage.

---

## Services

| ID  | Name                | Stack               | Role                                                                  |
|-----|---------------------|---------------------|-----------------------------------------------------------------------|
| MS1 | Media Processor     | Go                  | Consumes videos from S3, runs FFmpeg for chunking and frame sampling  |
| MS2 | AI Perception       | Python / FastAPI    | Generates timestamped multi-lingual transcripts and visual embeddings |
| MS3 | Search and Indexing | Python / FastAPI    | Indexes embeddings via pgvector, serves vector search and RAG context |
| MS4 | User Workflow API   | Node.js / Express   | Auth, presigned S3 uploads, video metadata, billing, job dispatch     |
| MS5 | Analytics           | Node.js             | Tracks per-user behavior, search patterns, and revisited segments     |
| MS6 | Agentic Brain       | Java / Spring Boot  | Multi-agent LLM pipeline for Q&A, summarization, and research        |
| MS7 | PDF Export          | Python / FastAPI    | Converts MS6 outputs into PDFs and uploads them to S3                 |

---

## Tech Stack

### Languages and Frameworks

| Layer           | Technology                              |
|-----------------|-----------------------------------------|
| Media ingestion | Go (high-concurrency worker)            |
| AI pipeline     | Python, FastAPI, Celery                 |
| Search layer    | Python, FastAPI, pgvector               |
| Orchestration   | Node.js, Express                        |
| Analytics       | Node.js                                 |
| Brain / RAG     | Java 21, Spring Boot, Spring AI         |
| PDF export      | Python, FastAPI, fpdf2                  |
| LLM provider    | Google Gemini (Flash / Pro)             |
| Embeddings      | Gemini Embeddings, Hugging Face models  |
| Transcription   | Whisper / Gemini Speech                 |
| Media tooling   | FFmpeg                                  |

### Data Layer

| Store      | Usage                                                                    |
|------------|--------------------------------------------------------------------------|
| PostgreSQL | User accounts, billing, video metadata (MS4); vector store via pgvector (MS3) |
| Redis      | Async job queue between MS4, MS1, MS2, MS3; Celery broker for MS2 tasks |
| AWS S3     | Raw video uploads, audio chunks, extracted keyframes, exported PDFs      |

### Infrastructure

| Tool / Platform | Purpose                                              |
|-----------------|------------------------------------------------------|
| Docker / Compose | Local multi-service orchestration                   |
| AWS Lambda      | Serverless deployment target for MS6                 |
| AWS API Gateway | Entry point routing to MS4 and MS6                   |
| Render          | Cloud deployment for Python and Node.js services     |
| Backblaze B2    | S3-compatible storage alternative for PDF exports    |

---

## How It Works

1. A user uploads a video. MS4 issues a presigned S3 URL so the upload goes directly to the bucket without passing through any application server.
2. MS4 registers the video in PostgreSQL and pushes a processing job to the Redis queue.
3. MS1 picks up the job, downloads the file from S3, and uses FFmpeg to extract audio segments and sample keyframes.
4. MS2 transcribes each audio segment (multi-lingual) and runs Gemini Vision on keyframes to produce text plus high-dimensional vector embeddings.
5. MS3 indexes all transcripts and embeddings using the pgvector extension, making content searchable at sub-second latency.
6. MS5 passively records user interactions to surface behavioral analytics and smart highlights.
7. When a user asks a question, MS4 routes it to MS6, which runs a multi-agent pipeline: Retriever pulls context from MS3, Analyzer extracts relevant facts, Synthesizer composes the answer, and CitationLinker maps claims back to video timestamps. For research queries a Planner agent first decomposes the topic into sub-queries before iterative retrieval.
8. After every MS6 response, an async fire-and-forget call is sent to MS7, which generates a formatted PDF report and returns a presigned S3 download URL.

---

## Local Development

Each service has its own README with individual setup instructions. To run the full stack:

```bash
docker compose up
```

The `docker-compose.yml` at the root starts all services along with PostgreSQL and Redis, with environment variables pre-wired. Copy `.env.example` files in each service directory and fill in your API keys before starting.
