import os
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routes.compatibility import router as compat_router
from app.routes.v1.router import router as v1_router
from app.services.ai.vector_store import VectorStore
from app.utils.logger import logger

# Enable verbose LangChain terminal logs dynamically
set_debug(settings.env == "development")

# Configure Redis connection settings for ARQ
redis_settings = RedisSettings(host=settings.redis_host, port=settings.redis_port)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    This replaces the deprecated @app.on_event("startup")
    """
    # Log credentials-safe active environment settings card on startup
    db_display = (
        settings.database_url.split("@")[-1]
        if "@" in settings.database_url
        else "configured"
    )
    logger.info(
        f"\n"
        f"  ==================================================\n"
        f"  🚀 Starting {settings.app_name}\n"
        f"  ├──  Environment  : {settings.env}\n"
        f"  ├──  Database URL  : {db_display}\n"
        f"  ├──  Qdrant URL   : {settings.qdrant_url}\n"
        f"  ├──  Redis Host   : {settings.redis_host}:{settings.redis_port}\n"
        f"  └──  Docs Status  : {'http://localhost:8001/docs' if settings.env == 'development' else 'disabled'}\n"
        f"  =================================================="
    )

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

# Constant for the frontend entry-point filename (avoids duplicated literal — S1192)
_INDEX_HTML = "index.html"

# MIDDLEWARES
# Note: Starlette processes add_middleware() in LIFO order, so the middleware
# added LAST here will run FIRST on every request.  CORS must be outermost
# (i.e., run first) so pre-flight OPTIONS requests are handled before any
# other middleware touches them (S8414).
app.add_middleware(SlowAPIMiddleware)

# 4. GZip Compression Middleware
# Compresses responses larger than 1000 bytes
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 3. Security Headers Middleware (sets secure headers)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Request Logging Middleware (logs request method, path, status, and latency)
app.add_middleware(RequestLoggingMiddleware)

# 1. CORS Middleware — added last so it is outermost (runs first)
allowed_origins_list = [
    o.strip() for o in settings.allowed_origins.split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# EXCEPTION HANDLERS
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ROUTES
app.include_router(v1_router, prefix="/api/v1")
app.include_router(compat_router)


# Serve static assets from frontend build if available
frontend_dist_path = "frontend/dist"
if os.path.exists(frontend_dist_path):
    app.mount(
        "/assets",
        StaticFiles(directory=f"{frontend_dist_path}/assets"),
        name="static_assets",
    )


@app.get("/")
async def root():
    """Serves the frontend index.html if present, otherwise returns health check."""
    # Check production build directory first
    prod_index = os.path.join(frontend_dist_path, _INDEX_HTML)
    if os.path.exists(prod_index):
        return FileResponse(prod_index)

    if os.path.exists(_INDEX_HTML):
        return FileResponse(_INDEX_HTML)
    return {"status": "healthy", "service": settings.app_name}
