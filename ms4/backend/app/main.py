from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import Base, engine
from .models import CallbackEvent, DeletedVideoCleanupLog, User, Video, WorkflowStatusLog
from .queues import redis_client
from .responses import error_response
from .routers import auth_router, internal_router, upload_router, videos_router
from .storage import ensure_bucket


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Ensure models are imported so metadata contains all tables.
    _ = (User, Video, WorkflowStatusLog, CallbackEvent, DeletedVideoCleanupLog)
    Base.metadata.create_all(bind=engine)
    ensure_bucket()
    yield
    try:
        redis_client.close()
    except Exception:
        pass


app = FastAPI(title="NeuroStream MS4 User Workflow Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    return error_response(str(exc.detail), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        loc = ".".join(str(item) for item in err.get("loc", []))
        messages.append(f"{loc}: {err.get('msg', 'Invalid value')}")
    return error_response(f"Validation failed: {'; '.join(messages)}", status_code=422)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    message = "An unexpected error occurred." if settings.node_env == "production" else str(exc)
    return error_response(message, status_code=500)


@app.get("/health")
def health_check():
    return {
        "success": True,
        "service": "ms4-user-workflow-service",
        "status": "ok",
    }


@app.get("/")
def root():
    return {
        "success": True,
        "service": "ms4-user-workflow-service",
        "message": "Service is running. Use /health for health checks.",
    }


app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(videos_router)
app.include_router(internal_router)


@app.api_route("/{path_name:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS", "HEAD"])
def catch_all(path_name: str):
    raise HTTPException(status_code=404, detail="Route not found.")
