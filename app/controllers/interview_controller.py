from sqlalchemy.ext.asyncio import AsyncSession

from app.services.interview import InterviewService


class InterviewController:
    @classmethod
    async def start_session(cls, db: AsyncSession, candidate_id: int, evaluation_id: int | None = None) -> dict:
        """
        Coordinates session setup and first question generation via InterviewService.
        """
        session, first_question = await InterviewService.create_session(
            db=db,
            candidate_id=candidate_id,
            evaluation_id=evaluation_id
        )
        return {
            "session_id": str(session.id),
            "status": session.status,
            "first_question": {
                "id": first_question.id,
                "question_text": first_question.question_text,
                "difficulty_level": first_question.difficulty_level,
                "question_order": first_question.question_order
            }
        }

    @classmethod
    async def submit_answer(cls, db: AsyncSession, question_id: int, answer_text: str) -> dict:
        """
        Submits answer, invokes LangGraph interview workflow, and returns graded evaluation.
        """
        return await InterviewService.submit_answer(
            db=db,
            question_id=question_id,
            answer_text=answer_text
        )
