from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db

router = APIRouter()

@router.get("/")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Standard check evaluating database connection health and system versions.
    """
    timestamp = datetime.now(UTC).isoformat()

    try:
        # Simple query to check Postgres connection
        await db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "postgres_connected": True,
            "timestamp": timestamp,
            "features": [
                "LangGraph Multi-Agent Workflows",
                "Qdrant Search Profiles",
                "Adaptive Interview Agent",
                "SQL Metrics Aggregations"
            ]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "postgres_connected": False,
            "error": str(e),
            "timestamp": timestamp
        }
