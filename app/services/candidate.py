import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.project_rec_agent import recommend_projects
from app.agents.resume_rewrite_agent import optimize_resume_bullets
from app.exceptions.custom_exceptions import NotFoundError
from app.graphs.state import SelfEvalState
from app.graphs.workflows import agentic_self_eval_app
from app.models.candidate import Candidate
from app.models.evaluation import Evaluation, EvaluationSkillGap
from app.models.rewrite_cache import ResumeRewriteCache
from app.utils.deduplication import compute_text_similarity
from app.utils.logger import logger

from app.constants.general import DEFAULT_DOMAIN, DEFAULT_GUEST, DEFAULT_NAME, DEFAULT_ROLE


class CandidateService:
    @classmethod
    async def parse_and_map_session_resume(cls, file_name: str, file_bytes: bytes, db: AsyncSession) -> dict:
        """
        Parses an uploaded resume in-memory and maps the fields into the exact adapter schema
        expected by the candidate dashboard portal.
        """
        from app.services.resume import ResumeService
        parsed_data = await ResumeService.parse_resume_session(file_name=file_name, file_bytes=file_bytes, db=db)

        mapped_skills = [
            s.get("skill_name") if isinstance(s, dict) else s
            for s in parsed_data.get("skills", [])
            if (s.get("skill_name") if isinstance(s, dict) else s)
        ]

        return {
            "status": "success",
            "message": "Resume parsed successfully (In-Memory Session)",
            "candidate_id": 0,
            "parsed_data": {
                "name": parsed_data.get("candidate_name") or DEFAULT_NAME,
                "email": parsed_data.get("email"),
                "phone_number": parsed_data.get("phone_number"),
                "role": parsed_data.get("primary_role_title"),
                "domain": parsed_data.get("primary_domain"),
                "experience": float(parsed_data.get("total_experience_years")) if parsed_data.get("total_experience_years") else 0.0,
                "highest_education": parsed_data.get("highest_education"),
                "summary_text": parsed_data.get("summary_text"),
                "skills": mapped_skills,
                "projects": parsed_data.get("projects") or [],
                "accomplishments": parsed_data.get("accomplishments") or [],
                "hobbies": parsed_data.get("hobbies") or [],
                "work_experience": parsed_data.get("work_experience") or []
            }
        }

    @classmethod
    async def agent_self_evaluate(cls, db: AsyncSession, candidate_id: int | None = None, candidate_data: dict | None = None, jd_text: str = "") -> dict:
        """
        Performs candidate self-evaluation using the LangGraph agent workflow.
        """
        if not candidate_id and not candidate_data:
            raise ValueError("Either candidate_id or candidate_data is required for self evaluation")

        profile = await cls._resolve_candidate_profile(db, candidate_id, candidate_data)

        initial_state = SelfEvalState(
            pdf_bytes=b"",
            jd_text=jd_text,
            resume_text=profile["summary"],
            score_100=0.0,
            strengths=[],
            gaps=[],
            interview_questions=[],
            role=profile["role"],
            domain=profile["domain"],
            skills_text=profile["skills_text"],
            experience_years=profile["experience"],
            education=profile["education"],
            learning_roadmap=[],
            confidence_feedback="",
            next_action="",
            decision_reasoning="",
            error="",
            current_step="started",
            parsed_resume={},
            candidate_text=""
        )

        final_state = await agentic_self_eval_app.ainvoke(initial_state)

        return {
            "score_100": final_state.get("score_100", 0.0),
            "strengths": final_state.get("strengths", []),
            "gaps": final_state.get("gaps", []),
            "interview_questions": final_state.get("interview_questions", []),
            "learning_roadmap": final_state.get("learning_roadmap", []),
            "confidence_feedback": final_state.get("confidence_feedback", "Completed"),
            "decision_reasoning": final_state.get("decision_reasoning", "Completed"),
            "status": "success" if not final_state.get("error") else "failed",
            "role": final_state.get("role", "N/A"),
            "domain": final_state.get("domain", "N/A")
        }

    @classmethod
    async def get_project_recommendations(
        cls,
        db: AsyncSession,
        candidate_id: int | None = None,
        candidate_data: dict | None = None,
        gaps: list[str] | None = None
    ) -> list[dict]:
        """
        Suggests targeted development projects to bridge candidate capability gaps.
        Calls recommend_projects agent directly without any hardcoded mock fail fallbacks.
        """
        profile = await cls._resolve_candidate_profile(db, candidate_id, candidate_data)

        gaps_list = gaps or []
        if not gaps_list and candidate_id and candidate_id > 0:
            gaps_res = await db.execute(
                select(EvaluationSkillGap.gap_text)
                .join(Evaluation, Evaluation.id == EvaluationSkillGap.evaluation_id)
                .where(Evaluation.candidate_id == candidate_id)
                .order_by(Evaluation.created_at.desc())
                .limit(5)
            )
            gaps_list = list(gaps_res.scalars().all())

        if not gaps_list:
            gaps_list = ["Software design", "Technical implementation"]

        return recommend_projects(
            role=profile["role"],
            experience_years=profile["experience"],
            skills=profile["skills_list"],
            gaps=gaps_list
        )

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
        Suggests rewrites and bullet points to improve the candidate's resume match.
        Includes a similarity-based caching check to bypass Groq calls if changes are minor.
        """
        profile = await cls._resolve_candidate_profile(db, candidate_id, candidate_data)

        # Target JD and Focus Areas normalization
        jd_norm = (jd_text or "General software engineering target").strip()
        focus_list = sorted(focus_areas or ["Action Verbs", "Metrics & Impact"])

        # Prepare cache keys
        cand_str = f"Summary: {profile['summary']}\nSkills: {profile['skills_list']}\nProjects: {profile['projects']}\nWork: {profile['work_experience']}"
        cand_hash = hashlib.sha256(cand_str.encode("utf-8")).hexdigest()
        jd_hash = hashlib.sha256(jd_norm.encode("utf-8")).hexdigest()
        focus_hash = hashlib.sha256(json.dumps(focus_list).encode("utf-8")).hexdigest()

        # Check rewrite cache
        cached_result = await cls._check_rewrite_cache(
            db, cand_str, cand_hash, jd_norm, jd_hash, focus_list, focus_hash
        )
        if cached_result is not None:
            return cached_result

        # Parse bullet points to optimize
        original_bullets = cls._extract_original_bullets(profile["work_experience"], profile["projects"])

        if not original_bullets:
            raise ValueError("No experience bullets or project descriptions available to optimize")

        # Invoke the rewrite agent dynamically via Groq
        result = optimize_resume_bullets(
            candidate_name=profile["name"],
            experience_years=profile["experience"],
            skills=profile["skills_list"],
            projects=profile["projects"],
            jd_text=jd_norm,
            focus_areas=focus_list
        )

        # Save to cache
        new_cache = ResumeRewriteCache(
            candidate_hash=cand_hash,
            jd_hash=jd_hash,
            focus_areas_hash=focus_hash,
            optimized_result_json=json.dumps(result),
            raw_jd_text=jd_norm,
            raw_candidate_text=cand_str
        )
        db.add(new_cache)
        await db.commit()

        return result

    # --- PRIVATE MODULARIZATION HELPERS ---

    @classmethod
    async def _resolve_candidate_profile(cls, db: AsyncSession, candidate_id: int | None, candidate_data: dict | None) -> dict:
        """Resolves candidate details from Postgres ID or direct JSON inputs to a unified format."""
        if candidate_id and candidate_id > 0:
            return await cls._resolve_profile_from_db(db, candidate_id)
        elif candidate_data:
            return cls._resolve_profile_from_dict(candidate_data)

        return cls._get_default_profile()

    @classmethod
    def _get_default_profile(cls) -> dict:
        """Returns standard default profile values."""
        return {
            "name": DEFAULT_GUEST,
            "experience": 2.0,
            "summary": "",
            "education": "",
            "role": DEFAULT_ROLE,
            "domain": DEFAULT_DOMAIN,
            "skills_text": "",
            "skills_list": [],
            "projects": [],
            "work_experience": []
        }

    @classmethod
    async def _resolve_profile_from_db(cls, db: AsyncSession, candidate_id: int) -> dict:
        """Fetches candidate from database and maps to standard dict."""
        candidate = await db.get(Candidate, candidate_id)
        if not candidate:
            raise NotFoundError(f"Candidate with ID {candidate_id} not found")

        return {
            "name": candidate.candidate_name or DEFAULT_NAME,
            "experience": float(candidate.total_experience_years) if candidate.total_experience_years else 0.0,
            "summary": candidate.summary_text or "",
            "education": candidate.highest_education or "",
            "role": candidate.primary_role_title or DEFAULT_ROLE,
            "domain": candidate.primary_domain or DEFAULT_DOMAIN,
            "skills_text": candidate.skills_text or "",
            "skills_list": [s.skill_name for s in candidate.skills] if candidate.skills else [],
            "projects": cls._parse_json_list(candidate.projects_json),
            "work_experience": cls._parse_json_list(candidate.work_experience_json)
        }

    @classmethod
    def _resolve_profile_from_dict(cls, candidate_data: dict) -> dict:
        """Parses dictionary candidate inputs to standard dict."""
        skills_list = []
        raw_skills = candidate_data.get("skills")
        if isinstance(raw_skills, list):
            skills_list = [s["skill_name"] if isinstance(s, dict) else s for s in raw_skills]
            skills_text = ", ".join(skills_list)
        else:
            skills_text = candidate_data.get("skills_text") or ""
            skills_list = [s.strip() for s in skills_text.split(",") if s.strip()]

        return {
            "name": candidate_data.get("name") or DEFAULT_NAME,
            "experience": float(candidate_data.get("total_experience_years") or candidate_data.get("experience") or 2.0),
            "summary": candidate_data.get("summary_text") or "",
            "education": candidate_data.get("highest_education") or "",
            "role": candidate_data.get("primary_role_title") or candidate_data.get("role") or DEFAULT_ROLE,
            "domain": candidate_data.get("primary_domain") or candidate_data.get("domain") or DEFAULT_DOMAIN,
            "skills_text": skills_text,
            "skills_list": skills_list,
            "projects": candidate_data.get("projects") or [],
            "work_experience": candidate_data.get("work_experience") or []
        }

    @classmethod
    def _parse_json_list(cls, json_str: str | None) -> list:
        """Safely parses JSON string as list fallback to empty list."""
        if not json_str:
            return []
        try:
            return json.loads(json_str)
        except Exception:
            return []

    @classmethod
    async def _check_rewrite_cache(
        cls, db: AsyncSession, cand_str: str, cand_hash: str, jd_norm: str, jd_hash: str, focus_list: list[str], focus_hash: str
    ) -> dict | None:
        """Checks if a matching optimized candidate profile rewrite exists in cache."""
        stmt = select(ResumeRewriteCache).where(
            ResumeRewriteCache.focus_areas_hash == focus_hash
        )
        cache_res = await db.execute(stmt)
        cache_entries = cache_res.scalars().all()

        for entry in cache_entries:
            cand_sim = 1.0 if entry.candidate_hash == cand_hash else compute_text_similarity(cand_str, entry.raw_candidate_text or "")
            jd_sim = 1.0 if entry.jd_hash == jd_hash else compute_text_similarity(jd_norm, entry.raw_jd_text or "")

            if cand_sim >= 0.95 and jd_sim >= 0.95:
                logger.info(f"Resume Rewrite Caching: Hit cache! Candidate Similarity={cand_sim * 100:.1f}%, JD Similarity={jd_sim * 100:.1f}%. Skipping Groq rewrite call.")
                return json.loads(entry.optimized_result_json)
        return None

    @classmethod
    def _extract_original_bullets(cls, work_exp_list: list[dict], projects_list: list[dict]) -> list[str]:
        """Extracts bullet points from work experience or project descriptions to optimize."""
        bullets = cls._extract_work_bullets(work_exp_list)
        if not bullets:
            bullets = cls._extract_project_bullets(projects_list)
        return bullets

    @classmethod
    def _extract_work_bullets(cls, work_exp_list: list[dict]) -> list[str]:
        """Extracts bullet points from work experience entries."""
        bullets = []
        if not work_exp_list:
            return bullets
        for job in work_exp_list:
            comp = job.get("company") or "Company"
            role_title = job.get("role") or "Role"
            for b in job.get("bullets", []):
                if b.strip():
                    bullets.append(f"{role_title} at {comp}: {b.strip()}")
        return bullets

    @classmethod
    def _extract_project_bullets(cls, projects_list: list[dict]) -> list[str]:
        """Extracts descriptions from projects list entries."""
        bullets = []
        if not projects_list:
            return bullets
        for p in projects_list:
            title = p.get("title") or p.get("project_title") or "Project"
            desc = p.get("description") or p.get("project_description") or ""
            if desc.strip():
                bullets.append(f"Project {title}: {desc.strip()}")
        return bullets
