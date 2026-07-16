
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.candidate import CandidateService


class CandidateController:
    @classmethod
    async def parse_and_map_session_resume(cls, file_name: str, file_bytes: bytes, db: AsyncSession) -> dict:
        """
        Parses an uploaded resume in-memory and delegates mapping to CandidateService.
        """
        return await CandidateService.parse_and_map_session_resume(file_name=file_name, file_bytes=file_bytes, db=db)

    @classmethod
    async def agent_self_evaluate(cls, db: AsyncSession, candidate_id: int | None = None, candidate_data: dict | None = None, jd_text: str = "") -> dict:
        """
        Performs candidate self-evaluation by delegating to CandidateService.
        """
        return await CandidateService.agent_self_evaluate(db=db, candidate_id=candidate_id, candidate_data=candidate_data, jd_text=jd_text)

    @classmethod
    async def get_project_recommendations(
        cls,
        db: AsyncSession,
        candidate_id: int | None = None,
        candidate_data: dict | None = None,
        gaps: list[str] | None = None
    ) -> list[dict]:
        """
        Suggests targeted development projects by delegating to CandidateService.
        """
        return await CandidateService.get_project_recommendations(db=db, candidate_id=candidate_id, candidate_data=candidate_data, gaps=gaps)

    @classmethod
    async def optimize_resume(
        cls,
        db: AsyncSession,
        candidate_id: int | None = None,
        candidate_data: dict | None = None,
        jd_text: str | None = None,
        focus_areas: list[str] | None = None
    ) -> dict:
        """
        Suggests rewrites and bullet points by delegating to CandidateService.
        """
        return await CandidateService.optimize_resume(
            db=db,
            candidate_id=candidate_id,
            candidate_data=candidate_data,
            jd_text=jd_text,
            focus_areas=focus_areas
        )
