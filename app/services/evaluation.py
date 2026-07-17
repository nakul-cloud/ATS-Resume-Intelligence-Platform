from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.evaluator import evaluate_candidate_against_jd
from app.config.settings import settings
from app.exceptions.custom_exceptions import AIServiceError
from app.models.candidate import Candidate
from app.models.evaluation import (
    DecisionBand,
    Evaluation,
    EvaluationComparison,
    EvaluationSkillGap,
    EvaluationStrength,
)
from app.services.ai.vector_store import VectorStore
from app.utils.logger import logger


class EvaluationService:
    _model = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """Lazily loads the SentenceTransformer embedding model."""
        if cls._model is None:
            logger.info(f"Loading SentenceTransformer model ({settings.embedding_model_name})...")
            cls._model = SentenceTransformer(settings.embedding_model_name)
        return cls._model

    @classmethod
    def _get_decision_band(cls, score: int) -> DecisionBand:
        """Maps an integer score (0-100) to a DecisionBand enum."""
        if score >= 80:
            return DecisionBand.HIGH
        if score >= 40:
            return DecisionBand.MEDIUM
        return DecisionBand.LOW

    @classmethod
    async def match_and_evaluate(
        cls, db: AsyncSession, jd_text: str, domain_filter: str | None = None, limit: int = 5
    ) -> list[dict]:
        """
        Executes a vector search in Qdrant for matching candidates,
        runs detailed LLM evaluations against the Job Description,
        and saves results in PostgreSQL.
        """
        logger.info("Starting JD matching and candidate evaluations...")

        # 1. Generate query embedding of the Job Description
        try:
            model = cls.get_model()
            jd_vector = model.encode(jd_text).tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding for Job Description: {e}")
            raise AIServiceError(f"Embedding generation failed: {e}") from e

        # 2. Query Qdrant for matching candidate vector profiles
        try:
            qdrant_results = await VectorStore.search_candidates(
                query_vector=jd_vector,
                limit=limit,
                domain=domain_filter
            )
        except Exception as e:
            logger.error(f"Qdrant vector search failed: {e}")
            raise AIServiceError(f"Vector search failed: {e}") from e

        logger.info(f"Qdrant returned {len(qdrant_results)} candidate matches.")
        if not qdrant_results:
            return []

        evaluation_results = []

        # 3. Process matches and run detail evaluations
        for rank, match in enumerate(qdrant_results, start=1):
            candidate_id = match.id
            similarity_score = match.score

            candidate = await cls._get_candidate(db, candidate_id)
            if not candidate:
                logger.warning(f"Candidate ID {candidate_id} found in Qdrant but missing in Postgres. Skipping.")
                continue

            # Check if this candidate has already been evaluated for this exact JD text
            exist_result = await db.execute(
                select(Evaluation).where(
                    Evaluation.candidate_id == candidate.id,
                    Evaluation.job_description_text == jd_text
                )
            )
            existing_eval = exist_result.scalar_one_or_none()

            # Prepare Candidate profile dictionary for agent
            c_dict = {
                "candidate_name": candidate.candidate_name,
                "primary_role_title": candidate.primary_role_title,
                "primary_domain": candidate.primary_domain,
                "total_experience_years": float(candidate.total_experience_years) if candidate.total_experience_years else 0.0,
                "highest_education": candidate.highest_education,
                "summary_text": candidate.summary_text,
                "skills_text": candidate.skills_text,
            }

            if existing_eval:
                logger.info(f"Retrieving cached evaluation for Candidate ID {candidate.id}...")
                eval_record = existing_eval
                eval_details = await cls._get_cached_evaluation(db, eval_record)
            else:
                eval_record, eval_details = await cls._create_new_evaluation(db, candidate.id, jd_text, c_dict)

            await cls._save_or_update_comparison(db, eval_record.id, candidate.id, similarity_score, rank)
            await db.commit()

            evaluation_results.append({
                "candidate_id": candidate.id,
                "candidate_name": candidate.candidate_name,
                "email": candidate.email,
                "phone_number": candidate.phone_number,
                "primary_role": candidate.primary_role_title,
                "primary_domain": candidate.primary_domain,
                "total_experience": float(candidate.total_experience_years) if candidate.total_experience_years else 0.0,
                "highest_education": candidate.highest_education,
                "summary_text": candidate.summary_text,
                "score_100": float(eval_details["score"]),
                "strengths": eval_details["strengths"],
                "gaps": eval_details["gaps"],
                "interview_questions": eval_details["interview_questions"],
                "skills": [s.skill_name for s in candidate.skills],
                "work_experience": cls._parse_json_field(candidate.work_experience_json),
                "projects": cls._parse_json_field(candidate.projects_json),
                "accomplishments": cls._parse_json_field(candidate.accomplishments_json),
                "hobbies": cls._parse_json_field(candidate.hobbies_json)
            })

        logger.info("Candidate matching and evaluations saved successfully.")
        return evaluation_results

    # --- PRIVATE MODULARIZATION HELPERS ---

    @classmethod
    async def _get_candidate(cls, db: AsyncSession, candidate_id: int) -> Candidate | None:
        """Fetches the candidate details from Postgres."""
        result = await db.execute(
            select(Candidate)
            .options(selectinload(Candidate.skills))
            .where(Candidate.id == candidate_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def _get_cached_evaluation(cls, db: AsyncSession, eval_record: Evaluation) -> dict:
        """Fetches and prepares structured data for an existing evaluation."""
        strengths_res = await db.execute(
            select(EvaluationStrength.strength_text).where(EvaluationStrength.evaluation_id == eval_record.id)
        )
        strengths = list(strengths_res.scalars().all())

        gaps_res = await db.execute(
            select(EvaluationSkillGap.gap_text).where(EvaluationSkillGap.evaluation_id == eval_record.id)
        )
        gaps = list(gaps_res.scalars().all())

        return {
            "score": eval_record.match_score,
            "strengths": strengths,
            "gaps": gaps,
            "interview_questions": [f"Targeted question about: {g}" for g in gaps][:3]
        }

    @classmethod
    async def _create_new_evaluation(cls, db: AsyncSession, candidate_id: int, jd_text: str, c_dict: dict) -> tuple[Evaluation, dict]:
        """Calls the evaluator agent and persists the new evaluation record to Postgres."""
        eval_details = evaluate_candidate_against_jd(c_dict, jd_text)
        match_score = eval_details["score"]
        decision_band = cls._get_decision_band(match_score)

        # Save Evaluation to Postgres
        eval_record = Evaluation(
            candidate_id=candidate_id,
            job_description_text=jd_text,
            match_score=match_score,
            decision_band=decision_band
        )
        db.add(eval_record)
        await db.flush()  # Generate eval_record.id

        # Save strengths
        for str_text in eval_details.get("strengths", []):
            db.add(EvaluationStrength(evaluation_id=eval_record.id, strength_text=str_text))

        # Save gaps
        for gap_text in eval_details.get("gaps", []):
            db.add(EvaluationSkillGap(evaluation_id=eval_record.id, gap_text=gap_text))

        return eval_record, eval_details

    @classmethod
    async def _save_or_update_comparison(cls, db: AsyncSession, eval_id: int, candidate_id: int, similarity_score: float, rank: int) -> None:
        """Updates or creates the EvaluationComparison record."""
        comp_result = await db.execute(
            select(EvaluationComparison).where(
                EvaluationComparison.evaluation_id == eval_id,
                EvaluationComparison.compared_candidate_id == candidate_id
            )
        )
        comparison = comp_result.scalar_one_or_none()

        if not comparison:
            comparison = EvaluationComparison(
                evaluation_id=eval_id,
                compared_candidate_id=candidate_id,
                similarity_score=similarity_score,
                rank=rank
            )
            db.add(comparison)
        else:
            comparison.similarity_score = similarity_score
            comparison.rank = rank

    @classmethod
    def _parse_json_field(cls, json_str: str | None) -> list:
        """Safely parses candidate JSON list attributes."""
        import json
        if not json_str:
            return []
        try:
            return json.loads(json_str)
        except Exception:
            return []
