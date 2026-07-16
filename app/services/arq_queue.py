from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config.settings import settings
from app.utils.logger import logger


class ArqQueueService:
    _pool: ArqRedis | None = None

    @classmethod
    async def get_pool(cls) -> ArqRedis:
        """
        Lazily initializes and returns a shared, singleton ARQ Redis connection pool.
        """
        if cls._pool is None:
            logger.info(
                f"[ArqQueueService] Initializing Redis connection pool on {settings.redis_host}:{settings.redis_port}"
            )
            redis_settings = RedisSettings(host=settings.redis_host, port=settings.redis_port)
            cls._pool = await create_pool(redis_settings)
        return cls._pool

    @classmethod
    async def enqueue_job(cls, function_name: str, *args, **kwargs) -> None:
        """
        Enqueues a background job using the shared connection pool.
        """
        pool = await cls.get_pool()
        logger.info(f"[ArqQueueService] Enqueuing job '{function_name}' with args={args} kwargs={kwargs}")
        await pool.enqueue_job(function_name, *args, **kwargs)
