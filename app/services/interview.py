"""
app/services/interview.py
Interview service — contains both stateful (InterviewService) and stateless (StatelessInterviewService)
mock interview logic.
"""
import json
import uuid
from typing import Any, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import MultipleResultsFound

from app.models.candidate import Candidate
from app.models.evaluation import Evaluation, EvaluationSkillGap
from app.models.interview import InterviewSession, InterviewQuestion, InterviewAnswer
from app.agents.interview_eval_agent import (
    generate_initial_question,
    generate_next_stateless_question,
    evaluate_interview_answer,
    generate_final_report,
)
from app.services.resume import ResumeService
from app.utils.logger import logger
from app.exceptions.custom_exceptions import NotFoundError, AIServiceError


# ---------------------------------------------------------------------------
# Stateful InterviewService (Original)
# ---------------------------------------------------------------------------

class InterviewService:
    MAX_QUESTIONS_PER_SESSION = 5

    @classmethod
    async def create_session(
        cls, db: AsyncSession, candidate_id: int, evaluation_id: int | None = None
    ) -> Tuple[InterviewSession, InterviewQuestion]:
        """
        Starts a new mock interview session for a candidate, identifies gaps,
        generates the initial question, and records it in the database.
        """
        logger.info(f"Initializing interview session for Candidate ID {candidate_id}...")
        
        # 1. Fetch Candidate
        candidate_res = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = candidate_res.scalar_one_or_none()
        if not candidate:
            raise NotFoundError(f"Candidate with ID {candidate_id} not found")

        role = candidate.primary_role_title or "Software Engineer"
        domain = candidate.primary_domain or "Technology"
        skills = candidate.skills_text or "General software skills"

        # 2. Retrieve Gaps (prioritize specific evaluation ID, fallback to latest evaluation)
        gaps = []
        if evaluation_id:
            eval_clause = select(EvaluationSkillGap.gap_text).where(EvaluationSkillGap.evaluation_id == evaluation_id)
        else:
            eval_clause = (
                select(EvaluationSkillGap.gap_text)
                .join(Evaluation, Evaluation.id == EvaluationSkillGap.evaluation_id)
                .where(Evaluation.candidate_id == candidate_id)
                .order_by(Evaluation.created_at.desc())
                .limit(5)
            )
        
        gaps_res = await db.execute(eval_clause)
        gaps = list(gaps_res.scalars().all())

        # 3. Call Agent to generate the first question
        try:
            initial_q = generate_initial_question(role, domain, skills, gaps)
        except Exception as e:
            logger.error(f"Failed to generate initial question: {e}")
            raise AIServiceError(f"Failed to generate first question: {e}") from e

        # 4. Create InterviewSession
        session = InterviewSession(
            candidate_id=candidate.id,
            evaluation_id=evaluation_id,
            status="IN_PROGRESS"
        )
        db.add(session)
        await db.flush()  # Generate session.id UUID

        # 5. Save first InterviewQuestion
        first_question = InterviewQuestion(
            session_id=session.id,
            question_text=initial_q["question_text"],
            difficulty_level=initial_q.get("difficulty_level", "MEDIUM"),
            question_order=1
        )
        db.add(first_question)
        
        await db.commit()
        await db.refresh(session)
        await db.refresh(first_question)
        
        logger.info(f"Interview session {session.id} started. First question generated.")
        return session, first_question

    @classmethod
    async def submit_answer(cls, db: AsyncSession, question_id: int, answer_text: str) -> dict:
        """
        Submits candidate's answer to a question, scores it via LLM,
        saves the evaluation, and dynamically generates the next question or completes the session.
        """
        logger.info(f"Processing answer submission for Question ID {question_id}...")

        # 1. Fetch Interview Question
        question_res = await db.execute(
            select(InterviewQuestion)
            .where(InterviewQuestion.id == question_id)
        )
        question = question_res.scalar_one_or_none()
        if not question:
            raise NotFoundError(f"Interview question with ID {question_id} not found")

        # Fetch session and candidate details
        session_res = await db.execute(
            select(InterviewSession).where(InterviewSession.id == question.session_id)
        )
        session = session_res.scalar_one_or_none()
        if not session or session.status != "IN_PROGRESS":
            raise AIServiceError("Interview session is not active or has already been completed")

        candidate_res = await db.execute(select(Candidate).where(Candidate.id == session.candidate_id))
        candidate = candidate_res.scalar_one_or_none()
        
        role = candidate.primary_role_title if candidate else "Software Engineer"
        domain = candidate.primary_domain if candidate else "Technology"

        # Check if question was already answered
        existing_answer = await db.execute(
            select(InterviewAnswer).where(InterviewAnswer.question_id == question.id)
        )
        if existing_answer.scalar_one_or_none():
            raise AIServiceError("This interview question has already been answered")

        # 2. Call LLM Evaluation Agent
        try:
            eval_res = evaluate_interview_answer(
                question_text=question.question_text,
                candidate_answer=answer_text,
                role=role,
                domain=domain,
                current_difficulty=question.difficulty_level
            )
        except Exception as e:
            logger.error(f"LLM answer evaluation failed: {e}")
            raise AIServiceError(f"LLM answer evaluation failed: {e}") from e

        # 3. Save InterviewAnswer
        answer = InterviewAnswer(
            question_id=question.id,
            answer_text=answer_text,
            feedback_text=eval_res.get("feedback"),
            score=eval_res.get("score"),
            follow_up_question=eval_res.get("follow_up_question")
        )
        db.add(answer)
        await db.flush()

        # 4. Handle Next Question generation or Session Completion
        next_difficulty = eval_res.get("next_difficulty", "MEDIUM")
        follow_up = eval_res.get("follow_up_question")
        
        # Check current question count
        count_res = await db.execute(
            select(func.count(InterviewQuestion.id))
            .where(InterviewQuestion.session_id == session.id)
        )
        current_question_count = count_res.scalar() or 1

        next_question_id = None
        status = "IN_PROGRESS"

        if current_question_count < cls.MAX_QUESTIONS_PER_SESSION and follow_up:
            # Create next dynamic question
            next_question = InterviewQuestion(
                session_id=session.id,
                question_text=follow_up,
                difficulty_level=next_difficulty,
                question_order=current_question_count + 1
            )
            db.add(next_question)
            await db.flush()
            next_question_id = next_question.id
        else:
            # Complete the session
            session.status = "COMPLETED"
            status = "COMPLETED"
            logger.info(f"Interview session {session.id} marked as COMPLETED.")

        await db.commit()

        return {
            "answer_score": float(answer.score) if answer.score is not None else 0.0,
            "feedback": answer.feedback_text,
            "strengths": eval_res.get("strengths", []),
            "weaknesses": eval_res.get("weaknesses", []),
            "follow_up_question": follow_up if status == "IN_PROGRESS" else None,
            "next_difficulty": next_difficulty if status == "IN_PROGRESS" else "MEDIUM",
            "next_question_id": next_question_id,
            "status": status
        }


# ---------------------------------------------------------------------------
# Tier helpers & resolution logic (for StatelessInterviewService)
# ---------------------------------------------------------------------------

def compute_score_tier(evaluation_score: float | None) -> str:
    """Map a 0-100 evaluation score to a tier key."""
    if evaluation_score is None:
        return "GAP_ANALYSIS"
    if evaluation_score < 30:
        return "FUNDAMENTALS"
    if evaluation_score < 60:
        return "BASIC"
    if evaluation_score < 80:
        return "GAP_ANALYSIS"
    return "ADVANCED"


def _upgrade_threshold(tier: str) -> float | None:
    """
    Returns the minimum avg interview score required to unlock the advanced round,
    or None if the tier never gets an advanced round.
    """
    return {
        "BASIC": None,        # No advanced round for BASIC tier
        "GAP_ANALYSIS": 70.0,
        "ADVANCED": 80.0,
    }.get(tier)


def _fallback_report(average_score: float, total_questions: int) -> dict[str, Any]:
    """Generates a minimal fallback report when the LLM call fails."""
    if average_score >= 80:
        msg = "Outstanding performance! Exceptional command of key concepts."
    elif average_score >= 70:
        msg = "Great job! Solid foundational knowledge. Keep challenging yourself."
    else:
        msg = "Good effort! Focus on bridging the identified weaknesses."

    return {
        "average_score": round(average_score, 1),
        "report_type": "combined" if total_questions > 5 else "basic",
        "confidence_feedback": msg,
        "strengths": [],
        "suggestions": [
            "Review weaknesses listed in the detailed round evaluations.",
            "Build the recommended projects to bridge technical hands-on gaps.",
            "Practice writing more structured responses for system-design questions.",
        ],
    }


async def _resolve_candidate(
    db: AsyncSession,
    candidate_id: int | None,
    candidate_data: dict[str, Any],
) -> Candidate:
    """
    Resolves a Candidate ORM object.
    """
    record = None

    if candidate_id:
        res = await db.execute(
            select(Candidate).where(Candidate.id == candidate_id).limit(1)
        )
        record = res.scalars().first()

    if not record and candidate_data:
        email = candidate_data.get("email")
        if email:
            res = await db.execute(
                select(Candidate).where(Candidate.email == email).limit(1)
            )
            record = res.scalars().first()

        if not record:
            record = await ResumeService.persist_parsed_candidate(db=db, data=candidate_data)

    if not record:
        res = await db.execute(select(Candidate).limit(1))
        record = res.scalars().first()

    if not record:
        record = Candidate(
            candidate_name=candidate_data.get("name") or "Candidate",
            email=candidate_data.get("email") or "candidate@example.com",
            primary_role_title=candidate_data.get("role") or "Software Engineer",
            primary_domain=candidate_data.get("domain") or "Tech",
        )
        db.add(record)
        await db.flush()

    return record


# ---------------------------------------------------------------------------
# StatelessInterviewService
# ---------------------------------------------------------------------------

class StatelessInterviewService:
    """
    Stateless mock interview service.
    Frontend maintains the full Q&A history; this service processes one
    request at a time and returns the next state.
    """

    @classmethod
    async def start_session(
        cls,
        db: AsyncSession,
        *,
        candidate_id: int | None,
        candidate_data: dict[str, Any],
        jd_text: str,
        gaps: list[str],
        evaluation_score: float | None,
        score_tier: str | None,
    ) -> dict[str, Any]:
        """
        Creates a new InterviewSession, generates the first question, and
        returns the session ID + first question data.
        """
        # Compute tier
        tier = score_tier or compute_score_tier(evaluation_score)

        if tier == "FUNDAMENTALS":
            raise ValueError(
                "FUNDAMENTALS_TIER: Score too low for mock interview. "
                "Focus on fundamentals first."
            )

        candidate = await _resolve_candidate(db, candidate_id, candidate_data)

        role = candidate.primary_role_title or "Software Developer"
        domain = candidate.primary_domain or "General Tech"
        skills_str = candidate.skills_text or ""

        q_data = generate_initial_question(
            role=role,
            domain=domain,
            skills=skills_str,
            gaps=gaps or [],
            tier=tier,
        )

        session = InterviewSession(candidate_id=candidate.id, status="IN_PROGRESS")
        db.add(session)
        await db.flush()

        first_q = InterviewQuestion(
            session_id=session.id,
            question_text=q_data["question_text"],
            difficulty_level=q_data.get("difficulty_level", "EASY"),
            question_order=1,
        )
        db.add(first_q)
        await db.commit()

        return {
            "status": "success",
            "session_id": str(session.id),
            "question_text": q_data["question_text"],
            "difficulty_level": q_data.get("difficulty_level", "EASY"),
            "score_tier": tier,
        }

    @classmethod
    async def submit_answer(
        cls,
        db: AsyncSession,
        *,
        session_id: str | None,
        candidate_id: int | None,
        candidate_data: dict[str, Any],
        jd_text: str,
        gaps: list[str],
        question_text: str,
        answer_text: str,
        difficulty_level: str,
        history: list[dict[str, Any]],
        is_advanced: bool,
        score_tier: str | None,
    ) -> dict[str, Any]:
        """
        Evaluates the candidate's answer, determines the next state, generates
        the next question or final report, and persists everything to Postgres.
        """
        candidate = candidate_data or {}
        role = candidate.get("primary_role_title") or candidate.get("role") or "Software Developer"
        domain = candidate.get("primary_domain") or candidate.get("domain") or "General Tech"
        tier = score_tier or "GAP_ANALYSIS"

        # Resolve DB session
        session = await cls._resolve_db_session(db, session_id)

        # Handle Complete sentinel
        if question_text == "Complete mock session":
            return await cls._complete_session(
                db=db,
                session=session,
                history=list(history or []),
                role=role,
                domain=domain,
            )

        # Evaluate the submitted answer
        eval_res = evaluate_interview_answer(
            question_text=question_text,
            candidate_answer=answer_text,
            role=role,
            domain=domain,
            current_difficulty=difficulty_level,
        )

        graded_item = {
            "question_text": question_text,
            "answer_text": answer_text,
            "answer_score": float(eval_res.get("score", 0.0)),
            "feedback": eval_res.get("feedback", ""),
            "strengths": eval_res.get("strengths", []),
            "weaknesses": eval_res.get("weaknesses", []),
            "difficulty_level": difficulty_level,
        }

        new_history = list(history or [])
        new_history.append(graded_item)

        scores = [h.get("answer_score", 0.0) for h in new_history]
        average_score = sum(scores) / len(scores) if scores else 0.0
        total_questions = len(new_history)

        # Determine next state
        next_question = None
        status = "IN_PROGRESS"
        can_upgrade = False

        if is_advanced:
            if total_questions < 8:
                q_data = generate_next_stateless_question(
                    candidate_profile=candidate,
                    jd_text=jd_text,
                    gaps=gaps or [],
                    history=new_history,
                    is_advanced=True,
                    tier=tier,
                )
                next_question = {
                    "question_text": q_data["question_text"],
                    "difficulty_level": q_data.get("difficulty_level", "HARD"),
                }
            else:
                status = "COMPLETED"

        else:
            if total_questions < 5:
                q_data = generate_next_stateless_question(
                    candidate_profile=candidate,
                    jd_text=jd_text,
                    gaps=gaps or [],
                    history=new_history,
                    is_advanced=False,
                    tier=tier,
                )
                next_question = {
                    "question_text": q_data["question_text"],
                    "difficulty_level": q_data.get("difficulty_level", "MEDIUM"),
                }
            else:
                threshold = _upgrade_threshold(tier)
                if threshold is not None and average_score >= threshold:
                    status = "UPGRADE_PROMPT"
                    can_upgrade = True
                else:
                    status = "COMPLETED"

        # Persist to Postgres
        await cls._persist_answer_and_next_question(
            db=db,
            session=session,
            question_text=question_text,
            answer_text=answer_text,
            graded_item=graded_item,
            next_question=next_question,
            status=status,
            total_questions=total_questions,
        )

        # Generate reports
        basic_report = None
        if status == "UPGRADE_PROMPT":
            basic_report = cls._generate_report_safe(
                role=role,
                domain=domain,
                history=new_history,
                report_type="basic",
                average_score=average_score,
                total_questions=total_questions,
            )

        final_report = None
        if status == "COMPLETED":
            final_report = cls._generate_report_safe(
                role=role,
                domain=domain,
                history=new_history,
                report_type="combined" if total_questions > 5 else "basic",
                average_score=average_score,
                total_questions=total_questions,
            )
            await cls._persist_final_report(db=db, session=session, final_report=final_report)

        if session:
            await db.commit()

        return {
            "status": status,
            "session_id": session_id,
            "answer_score": graded_item["answer_score"],
            "feedback": graded_item["feedback"],
            "strengths": graded_item["strengths"],
            "weaknesses": graded_item["weaknesses"],
            "next_question": next_question,
            "history": new_history,
            "can_upgrade": can_upgrade,
            "average_score": round(average_score, 1),
            "basic_report": basic_report,
            "final_report": final_report,
        }

    @staticmethod
    async def _resolve_db_session(
        db: AsyncSession, session_id: str | None
    ) -> InterviewSession | None:
        if not session_id:
            return None
        try:
            sess_uuid = uuid.UUID(session_id)
            res = await db.execute(
                select(InterviewSession).where(InterviewSession.id == sess_uuid)
            )
            return res.scalar_one_or_none()
        except Exception:
            return None

    @staticmethod
    async def _complete_session(
        db: AsyncSession,
        session: InterviewSession | None,
        history: list[dict[str, Any]],
        role: str,
        domain: str,
    ) -> dict[str, Any]:
        scores = [h.get("answer_score", 0.0) for h in history]
        average_score = sum(scores) / len(scores) if scores else 0.0
        total_questions = len(history)

        try:
            final_report = generate_final_report(role=role, domain=domain, history=history)
            final_report["average_score"] = round(average_score, 1)
            final_report["report_type"] = "combined" if total_questions > 5 else "basic"
        except Exception as e:
            logger.error(f"Failed to generate final report (complete sentinel): {e}")
            final_report = _fallback_report(average_score, total_questions)

        if session:
            session.status = "COMPLETED"
            session.average_score = final_report.get("average_score")
            session.confidence_feedback = final_report.get("confidence_feedback")
            session.suggestions = json.dumps(final_report.get("suggestions", []))
            session.strengths = json.dumps(final_report.get("strengths", []))
            await db.commit()

        return {
            "status": "COMPLETED",
            "answer_score": 0.0,
            "feedback": "Session completed.",
            "strengths": [],
            "weaknesses": [],
            "next_question": None,
            "history": history,
            "can_upgrade": False,
            "average_score": round(average_score, 1),
            "basic_report": None,
            "final_report": final_report,
        }

    @staticmethod
    def _generate_report_safe(
        role: str,
        domain: str,
        history: list[dict[str, Any]],
        report_type: str,
        average_score: float,
        total_questions: int,
    ) -> dict[str, Any]:
        try:
            report = generate_final_report(role=role, domain=domain, history=history)
            report["average_score"] = round(average_score, 1)
            report["report_type"] = report_type
            return report
        except Exception as e:
            logger.error(f"Report generation failed ({report_type}): {e}")
            return _fallback_report(average_score, total_questions)

    @staticmethod
    async def _persist_answer_and_next_question(
        db: AsyncSession,
        session: InterviewSession | None,
        question_text: str,
        answer_text: str,
        graded_item: dict[str, Any],
        next_question: dict[str, Any] | None,
        status: str,
        total_questions: int,
    ) -> None:
        if not session:
            return

        db_question = None
        res = await db.execute(
            select(InterviewQuestion)
            .where(InterviewQuestion.session_id == session.id)
            .where(InterviewQuestion.question_text == question_text)
        )
        db_question = res.scalar_one_or_none()

        if not db_question:
            res_latest = await db.execute(
                select(InterviewQuestion)
                .where(InterviewQuestion.session_id == session.id)
                .order_by(InterviewQuestion.question_order.desc())
                .limit(1)
            )
            db_question = res_latest.scalar_one_or_none()

        if db_question:
            db.add(InterviewAnswer(
                question_id=db_question.id,
                answer_text=answer_text,
                feedback_text=graded_item["feedback"],
                score=graded_item["answer_score"],
                follow_up_question=next_question["question_text"] if next_question else None,
            ))

        if next_question and status == "IN_PROGRESS":
            db.add(InterviewQuestion(
                session_id=session.id,
                question_text=next_question["question_text"],
                difficulty_level=next_question["difficulty_level"],
                question_order=total_questions + 1,
            ))

        if status == "COMPLETED":
            session.status = "COMPLETED"

        await db.flush()

    @staticmethod
    async def _persist_final_report(
        db: AsyncSession,
        session: InterviewSession | None,
        final_report: dict[str, Any],
    ) -> None:
        if not session:
            return
        session.average_score = final_report.get("average_score")
        session.confidence_feedback = final_report.get("confidence_feedback")
        session.suggestions = json.dumps(final_report.get("suggestions", []))
        session.strengths = json.dumps(final_report.get("strengths", []))
