import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.api.auth.routes import router as auth_router
from app.api.health import router as health_router
from app.core.config import settings
from app.utils.exceptions import DevTrackException
from app.core.logging import request_id_ctx, setup_logging

# 1. Initialize structured logging configuration
setup_logging()
logger = logging.getLogger("devtrack.app")


# 2. Application Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    logger.info(
        "DevTrack API starting up",
        extra={
            "extra_data": {
                "environment": settings.ENVIRONMENT,
                "version": "1.0.0",
                "log_level": settings.LOG_LEVEL,
            }
        },
    )
    yield
    logger.info("DevTrack API shutting down")


# 3. FastAPI Application Instance
app = FastAPI(
    title="DevTrack API",
    description="Unified Developer Analytics Platform Backend API",
    version="1.0.0",
    lifespan=lifespan,
)


# 4. HTTP Request Correlation and Logging Middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    """Extract or generate X-Request-ID and log HTTP request execution metrics."""
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_ctx.set(req_id)
    start_time = time.perf_counter()

    try:
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.info(
            f"{request.method} {request.url.path} completed with status {response.status_code}",
            extra={
                "extra_data": {
                    "http_method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            },
        )
        response.headers["X-Request-ID"] = req_id
        return response
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.exception(
            f"Unhandled exception during {request.method} {request.url.path}",
            extra={
                "extra_data": {
                    "http_method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                }
            },
        )
        raise exc
    finally:
        request_id_ctx.reset(token)


# 5. Base Route
@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "DevTrack API is running"}


# 6. Custom Exception Handlers
@app.exception_handler(DevTrackException)
async def devtrack_exception_handler(request: Request, exc: DevTrackException) -> JSONResponse:
    """Handle custom application exceptions and format them consistently."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id_ctx.get()
            }
        }
    )


# 7. Registered API Routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth")
