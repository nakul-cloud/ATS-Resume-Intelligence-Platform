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
                "name": parsed_data.get("candidate_name") or "Candidate",
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
        if candidate_id and candidate_id > 0:
            candidate = await db.get(Candidate, candidate_id)
            if not candidate:
                raise NotFoundError(f"Candidate with ID {candidate_id} not found")
            summary = candidate.summary_text or ""
            role = candidate.primary_role_title or ""
            domain = candidate.primary_domain or ""
            skills = candidate.skills_text or ""
            experience = float(candidate.total_experience_years) if candidate.total_experience_years else 0.0
            education = candidate.highest_education or ""
        elif candidate_data:
            summary = candidate_data.get("summary_text") or ""
            role = candidate_data.get("primary_role_title") or candidate_data.get("role") or ""
            domain = candidate_data.get("primary_domain") or candidate_data.get("domain") or ""
            skills = ", ".join([s["skill_name"] if isinstance(s, dict) else s for s in candidate_data.get("skills", [])]) if isinstance(candidate_data.get("skills"), list) else (candidate_data.get("skills_text") or "")
            experience = float(candidate_data.get("total_experience_years") or candidate_data.get("experience") or 0.0)
            education = candidate_data.get("highest_education") or ""
        else:
            raise ValueError("Either candidate_id or candidate_data is required for self evaluation")

        initial_state = SelfEvalState(
            pdf_bytes=b"",
            jd_text=jd_text,
            resume_text=summary,
            score_100=0.0,
            strengths=[],
            gaps=[],
            interview_questions=[],
            role=role,
            domain=domain,
            skills_text=skills,
            experience_years=experience,
            education=education,
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
        role = "Software Developer"
        experience = 2.0
        skills_list = []
        gaps_list = gaps or []

        if candidate_id and candidate_id > 0:
            candidate = await db.get(Candidate, candidate_id)
            if candidate:
                role = candidate.primary_role_title or role
                experience = float(candidate.total_experience_years) if candidate.total_experience_years else experience
                skills_list = [s.skill_name for s in candidate.skills] if candidate.skills else []
                if not gaps_list:
                    gaps_res = await db.execute(
                        select(EvaluationSkillGap.gap_text)
                        .join(Evaluation, Evaluation.id == EvaluationSkillGap.evaluation_id)
                        .where(Evaluation.candidate_id == candidate_id)
                        .order_by(Evaluation.created_at.desc())
                        .limit(5)
                    )
                    gaps_list = list(gaps_res.scalars().all())
        elif candidate_data:
            role = candidate_data.get("primary_role_title") or candidate_data.get("role") or role
            experience = float(candidate_data.get("total_experience_years") or candidate_data.get("experience") or experience)
            raw_skills = candidate_data.get("skills", [])
            skills_list = [s["skill_name"] if isinstance(s, dict) else s for s in raw_skills] if isinstance(raw_skills, list) else []

        if not gaps_list:
            gaps_list = ["Software design", "Technical implementation"]

        return recommend_projects(
            role=role,
            experience_years=experience,
            skills=skills_list,
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
        name = "Guest Candidate"
        experience = 2.0
        summary = ""
        skills_list = []
        projects_list = []
        work_exp_list = []

        if candidate_id and candidate_id > 0:
            candidate = await db.get(Candidate, candidate_id)
            if candidate:
                name = candidate.candidate_name or "Candidate"
                experience = float(candidate.total_experience_years or 0)
                summary = candidate.summary_text or ""
                skills_list = [candidate.skills_text] if candidate.skills_text else []
                try:
                    projects_list = json.loads(candidate.projects_json) if candidate.projects_json else []
                except Exception:
                    projects_list = []
                try:
                    work_exp_list = json.loads(candidate.work_experience_json) if candidate.work_experience_json else []
                except Exception:
                    work_exp_list = []
        elif candidate_data:
            name = candidate_data.get("name") or "Candidate"
            experience = float(candidate_data.get("experience") or 2.0)
            summary = candidate_data.get("summary_text") or ""
            skills_list = candidate_data.get("skills") or []
            projects_list = candidate_data.get("projects") or []
            work_exp_list = candidate_data.get("work_experience") or []

        # Target JD and Focus Areas normalization
        jd_norm = (jd_text or "General software engineering target").strip()
        focus_list = sorted(focus_areas or ["Action Verbs", "Metrics & Impact"])

        # Prepare cache keys
        cand_str = f"Summary: {summary}\nSkills: {skills_list}\nProjects: {projects_list}\nWork: {work_exp_list}"
        cand_hash = hashlib.sha256(cand_str.encode("utf-8")).hexdigest()
        jd_hash = hashlib.sha256(jd_norm.encode("utf-8")).hexdigest()
        focus_hash = hashlib.sha256(json.dumps(focus_list).encode("utf-8")).hexdigest()

        # Check rewrite cache
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

        # Parse bullet points to optimize
        original_bullets = []
        if work_exp_list:
            for job in work_exp_list:
                comp = job.get("company") or "Company"
                role_title = job.get("role") or "Role"
                bullets = job.get("bullets") or []
                for b in bullets:
                    if b.strip():
                        original_bullets.append(f"{role_title} at {comp}: {b.strip()}")
        if not original_bullets and projects_list:
            for p in projects_list:
                title = p.get("title") or p.get("project_title") or "Project"
                desc = p.get("description") or p.get("project_description") or ""
                if desc.strip():
                    original_bullets.append(f"Project {title}: {desc.strip()}")

        if not original_bullets:
            raise ValueError("No experience bullets or project descriptions available to optimize")

        # Invoke the rewrite agent dynamically via Groq
        result = optimize_resume_bullets(
            candidate_name=name,
            experience_years=experience,
            summary=summary,
            skills=skills_list,
            projects=projects_list,
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
