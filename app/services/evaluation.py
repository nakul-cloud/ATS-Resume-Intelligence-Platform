from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sentence_transformers import SentenceTransformer

from app.models.candidate import Candidate
from app.models.evaluation import Evaluation, EvaluationStrength, EvaluationSkillGap, EvaluationComparison, DecisionBand
from app.agents.evaluator import evaluate_candidate_against_jd
from app.services.ai.vector_store import VectorStore
from app.config.settings import settings
from app.utils.logger import logger
from app.exceptions.custom_exceptions import AIServiceError, NotFoundError

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
        elif score >= 40:
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

            # Fetch candidate details from Postgres
            result = await db.execute(
                select(Candidate)
                .options(selectinload(Candidate.skills))
                .where(Candidate.id == candidate_id)
            )
            candidate = result.scalar_one_or_none()
            
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
                
                # Fetch related strengths, gaps
                strengths_res = await db.execute(
                    select(EvaluationStrength.strength_text).where(EvaluationStrength.evaluation_id == eval_record.id)
                )
                strengths = list(strengths_res.scalars().all())
                
                gaps_res = await db.execute(
                    select(EvaluationSkillGap.gap_text).where(EvaluationSkillGap.evaluation_id == eval_record.id)
                )
                gaps = list(gaps_res.scalars().all())
                
                # Generate dynamic interview questions on-the-fly or fallback
                # For simplicity, we run the evaluator agent if cached lists are empty, or use placeholders
                eval_details = {
                    "score": eval_record.match_score,
                    "strengths": strengths,
                    "gaps": gaps,
                    "interview_questions": [f"Targeted question about: {g}" for g in gaps][:3]
                }
            else:
                # Call Evaluator Agent
                eval_details = evaluate_candidate_against_jd(c_dict, jd_text)
                match_score = eval_details["score"]
                decision_band = cls._get_decision_band(match_score)

                # Save Evaluation to Postgres
                eval_record = Evaluation(
                    candidate_id=candidate.id,
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

            # Update or create EvaluationComparison (tracks the current search rank)
            comp_result = await db.execute(
                select(EvaluationComparison).where(
                    EvaluationComparison.evaluation_id == eval_record.id,
                    EvaluationComparison.compared_candidate_id == candidate.id
                )
            )
            comparison = comp_result.scalar_one_or_none()

            if not comparison:
                comparison = EvaluationComparison(
                    evaluation_id=eval_record.id,
                    compared_candidate_id=candidate.id,
                    similarity_score=similarity_score,
                    rank=rank
                )
                db.add(comparison)
            else:
                comparison.similarity_score = similarity_score
                comparison.rank = rank

            await db.commit()

            # Compile response schema fields
            import json
            work_exp = json.loads(candidate.work_experience_json) if candidate.work_experience_json else []
            projects = json.loads(candidate.projects_json) if candidate.projects_json else []
            accomplishments = json.loads(candidate.accomplishments_json) if candidate.accomplishments_json else []
            hobbies = json.loads(candidate.hobbies_json) if candidate.hobbies_json else []

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
                "work_experience": work_exp,
                "projects": projects,
                "accomplishments": accomplishments,
                "hobbies": hobbies
            })

        logger.info("Candidate matching and evaluations saved successfully.")
        return evaluation_results
