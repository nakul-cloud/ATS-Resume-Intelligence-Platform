import uvicorn

from app.config.settings import settings
from app.utils.logger import logger

if __name__ == "__main__":
    logger.info(f"Starting Uvicorn server on port {settings.port}...")

    # Bind to localhost in development, 0.0.0.0 only when explicitly requested
    # via SERVER_HOST env-var (e.g. inside Docker / production deployments).
    import os
    host = os.getenv("SERVER_HOST", "127.0.0.1" if settings.env == "development" else "0.0.0.0")

    # Run the FastAPI app via Uvicorn
    # This acts exactly like app.listen() in Node.js
    uvicorn.run(
        "app.main:app",
        host=host,
        port=settings.port,  # Picks up PORT from .env
        reload=settings.env == "development",  # Auto-restart on code changes in dev
        log_level="debug" if settings.env == "development" else "warning",
    )
