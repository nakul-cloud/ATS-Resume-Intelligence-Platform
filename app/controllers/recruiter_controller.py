
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.evaluation import EvaluationService
from app.services.jd import JDService
from app.services.metrics import MetricsService


class RecruiterController:
    @classmethod
    async def get_live_metrics(cls, db: AsyncSession) -> dict:
        """
        Coordinateslive system distribution and activity history queries via MetricsService.
        """
        return await MetricsService.get_dashboard_metrics(db=db)

    @classmethod
    async def evaluate_jd(cls, db: AsyncSession, jd_text: str, domain: str | None = None, top_k: int = 5) -> dict:
        """
        Finds and scores candidate matches against Job Description queries.
        """
        return await EvaluationService.match_and_evaluate(
            db=db,
            jd_text=jd_text,
            domain_filter=domain,
            limit=top_k
        )

    @classmethod
    async def normalize_jd(cls, db: AsyncSession, jd_text: str) -> dict:
        """
        Structures messy job description text using JDService normalization.
        """
        return await JDService.normalize_job_description(db=db, jd_text=jd_text)
