from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.services.ai.vector_store import VectorStore
from app.utils.logger import logger
from app.routes.v1.router import router as v1_router
from app.routes.compatibility import router as compat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    logger.info("Initializing application services...")
    try:
        # Initialize the Qdrant collection and indices
        VectorStore.init_collection()
        logger.info("Qdrant database connection and collections initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize Qdrant service: {e}")
        
    yield
    
    logger.info("Shutting down application services...")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(v1_router, prefix="/api/v1")
app.include_router(compat_router)


from app.exceptions.custom_exceptions import AppError
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.exceptions.handlers import (
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)


from fastapi.responses import FileResponse
import os

@app.get("/")
async def root():
    """Serves the frontend index.html if present, otherwise returns health check."""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "healthy", "service": settings.app_name}
