from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config.settings import settings

# Initialize slowapi rate limiter using Redis backend for distributed limit tracking
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{settings.redis_host}:{settings.redis_port}/1"
)
