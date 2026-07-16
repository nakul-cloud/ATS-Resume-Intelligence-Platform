from arq.connections import RedisSettings

from app.config.settings import settings
from worker.tasks.resume_tasks import ingest_resume_job, persist_candidate_job

# Configure Redis connection for ARQ
redis_settings = RedisSettings(
    host=settings.redis_host,
    port=settings.redis_port
)

class WorkerSettings:
    # Register background task handlers
    functions = [ingest_resume_job, persist_candidate_job]  # noqa: RUF012
    redis_settings = redis_settings

    # Limit concurrent jobs
    max_jobs = 5

    # Prevent arq from auto-retrying failed jobs to avoid cascading failure loops
    max_tries = 1

    # Hard ceiling for task execution (Slightly above internal 600s timeout)
    job_timeout = 630
