from qdrant_client import AsyncQdrantClient

from app.config.settings import settings

_client: AsyncQdrantClient | None = None

def get_qdrant() -> AsyncQdrantClient:
    """
    Returns the initialized Qdrant async client singleton.
    Ensure init_qdrant() is called during application startup/lifespan.
    """
    if _client is None:
        raise RuntimeError("Qdrant client not initialized. Call init_qdrant() first.")
    return _client

def init_qdrant() -> AsyncQdrantClient:
    """
    Initialize the Qdrant async client singleton.
    """
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=settings.qdrant_url)
    return _client

async def close_qdrant() -> None:
    """
    Safely close the Qdrant async client.
    """
    global _client
    if _client is not None:
        await _client.close()
        _client = None
