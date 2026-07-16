import os
from contextlib import asynccontextmanager

import secure
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from langchain_core.globals import set_debug
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.database import engine
from app.config.rate_limiter import limiter
from app.config.settings import settings
from app.exceptions.custom_exceptions import AppError
from app.exceptions.handlers import (
    app_error_handler,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.routes.compatibility import router as compat_router
from app.routes.v1.router import router as v1_router
from app.services.ai.vector_store import VectorStore
from app.utils.logger import logger

# Enable verbose LangChain terminal logs globally
set_debug(True)

# Initialize the secure package (Helmet equivalent)
secure_headers = secure.Secure()

# Configure Redis connection settings for ARQ
redis_settings = RedisSettings(
    host=settings.redis_host,
    port=settings.redis_port
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    This replaces the deprecated @app.on_event("startup")
    """
    logger.info(f"Starting {settings.app_name} in {settings.env} mode...")

    # Check Database connection on startup
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successfully established.")
    except Exception as e:
        logger.critical(f"Database connection failed: {e}")
        raise

    # Initialize the Qdrant collection and indices
    try:
        VectorStore.init_collection()
        logger.info("Qdrant database connection and collections initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize Qdrant service: {e}")
        raise

    # Validate Groq API Key is present before accepting any requests
    if not settings.groq_api_key:
        logger.critical(
            "GROQ_API_KEY is not set in environment. AI features will not work."
        )
        raise RuntimeError("GROQ_API_KEY is required to start this application.")
    logger.info("Groq API key validated successfully.")

    # Initialize Global Redis Pool for background tasks
    try:
        app.state.redis_pool = await create_pool(redis_settings)
        logger.info("Global Redis pool for background tasks initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize Redis pool: {e}")
        raise

    yield  # Application runs here

    # Shutdown events
    logger.info("Shutting down application...")

    if hasattr(app.state, "redis_pool"):
        await app.state.redis_pool.aclose()
        logger.info("Redis pool closed.")

    await engine.dispose()
    logger.info("Database connections closed.")


# Initialize FastAPI App
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    # Automatically disable Swagger docs in production for security
    docs_url="/docs" if settings.env == "development" else None,
    redoc_url="/redoc" if settings.env == "development" else None,
    openapi_url="/openapi.json" if settings.env == "development" else None,
    lifespan=lifespan,
)


# Wire up the rate limiter
app.state.limiter = limiter

# MIDDLEWARES
app.add_middleware(SlowAPIMiddleware)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# 2. GZip Compression Middleware
# Compresses responses larger than 1000 bytes
app.add_middleware(GZipMiddleware, minimum_size=1000)


# 3. Security Headers Middleware
@app.middleware("http")
async def set_secure_headers(request: Request, call_next):
    """Applies security headers to every response"""
    response = await call_next(request)
    secure_headers.set_headers(response)
    return response


# EXCEPTION HANDLERS
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ROUTES
app.include_router(v1_router, prefix="/api/v1")
app.include_router(compat_router)


@app.get("/")
async def root():
    """Serves the frontend index.html if present, otherwise returns health check."""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "healthy", "service": settings.app_name}
