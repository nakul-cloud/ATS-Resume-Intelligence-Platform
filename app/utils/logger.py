# app/utils/logger.py
import sys
from loguru import logger

# Remove the default logger configuration
logger.remove()

# Add a standard stdout console handler with clean formatting
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    backtrace=True,
    diagnose=True,
)

# Add a serialized JSON file logger sink
logger.add(
    "application.json",
    serialize=True,
    level="DEBUG",
    rotation="10 MB",
)

# Export the logger singleton
__all__ = ["logger"]
