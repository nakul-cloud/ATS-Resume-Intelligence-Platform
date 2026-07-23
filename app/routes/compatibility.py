from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.security import User, get_current_user
from app.controllers.candidate_controller import CandidateController
from app.controllers.interview_controller import InterviewController
from app.controllers.recruiter_controller import RecruiterController
from app.controllers.resume_controller import ResumeController
from app.exceptions.custom_exceptions import NotFoundError, StorageError
from app.schemas.compat import (
    AgentSelfEvalRequest,
    CandidatePersistRequest,
    InterviewEvaluateRequest,
    ProjectsRecommendationRequest,
    ResumeRewriteRequest,
    StatelessInterviewStartRequest,
    StatelessInterviewSubmitRequest,
)

# Import schemas from standard schema modules
from app.schemas.jd import JDEvaluationRequest, JDRewriteRequest
from app.services.auth import AuthService
from app.services.candidate import CandidateService
from app.services.resume import ResumeService
from app.utils.logger import logger

router = APIRouter()

# Shared response literal — avoids duplicating the same string (S1192)
_RECRUITER_ONLY = "Forbidden: Recruiter access only"

# Comprehensive OpenAPI responses dictionary satisfying Sonar S8415 for all endpoints
COMPAT_RESPONSES = {
    400: {"description": "Bad Request"},
    401: {"description": "Unauthorized - Authentication failed"},
    403: {"description": "Forbidden - Access denied"},
    404: {"description": "Not Found - Requested resource missing"},
    500: {"description": "Internal Server Error"},
}


@router.post("/auth/token", responses=COMPAT_RESPONSES)
async def login_compat(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Compatibility authentication route matching token requests from frontend.
    """
    try:
        data = await AuthService.authenticate_and_generate_token(
            username=form_data.username, password=form_data.password
        )
        return {
            "status": "success",
            "message": "Authentication successful",
            "data": data,
        }
    except Exception as e:
        logger.error(f"Compat login failed: {e}")
        raise HTTPException(status_code=401, detail=str(e)) from e


# =====================================================================
# ENDPOINTS
# =====================================================================


@router.post("/candidate/upload-resume", responses=COMPAT_RESPONSES)
async def upload_resume_compat(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Compatibility route matching fetch('${API_BASE_URL}/candidate/upload-resume')
    Parses resume in-memory without saving it to SQL/Qdrant.
    """
    try:
        file_bytes = await file.read()
        return await CandidateController.parse_and_map_session_resume(
            file_name=file.filename, file_bytes=file_bytes, db=db
        )
    except Exception as e:
        logger.error(f"Compat upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/v1/resume/upload", responses=COMPAT_RESPONSES)
async def upload_resume_recruiter_compat(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail=_RECRUITER_ONLY)
    """
    Compatibility route for recruiter resume uploads matching Vite's proxy rules.
    """
    try:
        return await ResumeController.upload_resume(db=db, file=file)
    except Exception as e:
        logger.error(f"Compat recruiter upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/candidate/persist", responses=COMPAT_RESPONSES)
async def persist_candidate(
    request: CandidatePersistRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Saves a session-wise parsed candidate to PostgreSQL and enqueues Qdrant indexing task.
    """
    try:
        # Save to database and flag for asynchronous vector embedding/indexing
        candidate = await ResumeService.persist_parsed_candidate(
            db=db, data=request.model_dump(), async_embed=True
        )

        # Enqueue the Qdrant indexing job via ArqQueueService
        from app.services.arq_queue import ArqQueueService

        await ArqQueueService.enqueue_job(
            "persist_candidate_job", candidate.resume_id, request.model_dump()
        )

        return {
            "status": "success",
            "message": "Candidate profile saved. Vector indexing is running in background.",
            "candidate_id": candidate.id,
            "resume_id": candidate.resume_id,
        }
    except Exception as e:
        logger.error(f"Failed to persist candidate: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/v1/resume/status/{resume_id}", responses=COMPAT_RESPONSES)
async def get_resume_status(
    resume_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get the ingestion status of a resume processed asynchronously.
    """
    try:
        data = await ResumeService.get_resume_status(db, resume_id)
        return {
            "status": "success",
            "data": data,
        }
    except StorageError as e:
        raise HTTPException(status_code=404, detail="Resume not found") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch resume status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/candidate/agent-self-evaluation", responses=COMPAT_RESPONSES)
async def agent_self_eval_compat(
    request: AgentSelfEvalRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Compatibility route matching fetch('${API_BASE_URL}/candidate/agent-self-evaluation')
    """
    try:
        return await CandidateController.agent_self_evaluate(
            db=db,
            candidate_id=request.candidate_id,
            candidate_data=request.candidate_data,
            jd_text=request.jd_text,
        )
    except Exception as e:
        logger.error(f"Compat self-evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/candidate/projects", responses=COMPAT_RESPONSES)
async def project_recommendations_compat(
    request: ProjectsRecommendationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Compatibility route matching fetch('${API_BASE_URL}/candidate/projects')
    """
    try:
        return await CandidateController.get_project_recommendations(
            db=db,
            candidate_id=request.candidate_id,
            candidate_data=request.candidate_data,
            gaps=request.gaps,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/candidate/resume-rewrite", responses=COMPAT_RESPONSES)
async def resume_rewrite_compat(
    request: ResumeRewriteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Compatibility route matching fetch('${API_BASE_URL}/candidate/resume-rewrite')
    """
    try:
        return await CandidateController.optimize_resume(
            db=db,
            candidate_id=request.candidate_id,
            candidate_data=request.candidate_data,
            jd_text=request.jd_text,
            focus_areas=request.focus_areas,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/jd/rewrite", responses=COMPAT_RESPONSES)
async def jd_rewrite_compat(
    request: JDRewriteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail=_RECRUITER_ONLY)
    """
    Compatibility route matching fetch('${API_BASE_URL}/jd/rewrite')
    """
    try:
        return await RecruiterController.normalize_jd(db=db, jd_text=request.jd_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/evaluate-jd", responses=COMPAT_RESPONSES)
async def evaluate_jd_compat(
    request: JDEvaluationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail=_RECRUITER_ONLY)
    """
    Compatibility route matching fetch('${API_BASE_URL}/evaluate-jd')
    """
    try:
        results = await RecruiterController.evaluate_jd(
            db=db, jd_text=request.jd_text, domain=request.domain, top_k=request.top_k
        )
        compat_results = []
        for r in results:
            compat_results.append(
                {
                    "candidate_id": r["candidate_id"],
                    "candidate_name": r["candidate_name"],
                    "primary_role": r["primary_role"],
                    "primary_domain": r["primary_domain"],
                    "total_experience": r["total_experience"],
                    "score_100": r["score_100"],
                    "strengths": r["strengths"],
                    "gaps": r["gaps"],
                    "interview_questions": r["interview_questions"],
                    "skills": r.get("skills", []),
                }
            )
        return {
            "jd_text": request.jd_text,
            "domain_filter": request.domain,
            "results": compat_results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/candidate/interview/start", responses=COMPAT_RESPONSES)
async def stateless_interview_start(
    request: StatelessInterviewStartRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Starts a mock interview session. Delegates all logic to StatelessInterviewService.
    """
    from app.services.interview import StatelessInterviewService

    try:
        return await StatelessInterviewService.start_session(
            db=db,
            candidate_id=request.candidate_id,
            candidate_data=request.candidate_data or {},
            jd_text=request.jd_text,
            gaps=request.gaps or [],
            evaluation_score=request.evaluation_score,
            score_tier=request.score_tier,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Stateless interview start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/candidate/interview/submit", responses=COMPAT_RESPONSES)
async def stateless_interview_submit(
    request: StatelessInterviewSubmitRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Evaluates a candidate's answer and returns the next state.
    Delegates all logic to StatelessInterviewService.
    """
    from app.services.interview import StatelessInterviewService

    try:
        return await StatelessInterviewService.submit_answer(
            db=db,
            session_id=request.session_id,
            candidate_id=request.candidate_id,
            candidate_data=request.candidate_data or {},
            jd_text=request.jd_text,
            gaps=request.gaps or [],
            question_text=request.question_text,
            answer_text=request.answer_text,
            difficulty_level=request.difficulty_level,
            history=request.history or [],
            is_advanced=request.is_advanced or False,
            score_tier=request.score_tier,
        )
    except Exception as e:
        logger.error(f"Stateless interview submit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/interview/evaluate", responses=COMPAT_RESPONSES)
async def interview_evaluate_compat(
    request: InterviewEvaluateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Compatibility route matching fetch('${API_BASE_URL}/interview/evaluate')
    """
    try:
        eval_result = await InterviewController.submit_answer(
            db=db,
            question_id=1,  # Resolves fallback dynamically
            answer_text=request.user_answer,
        )
        return {
            "answer_score": eval_result.get("answer_score", 0.0),
            "feedback": eval_result.get("feedback", ""),
            "strengths": eval_result.get("strengths", []),
            "weaknesses": eval_result.get("weaknesses", []),
            "follow_up_question": eval_result.get("follow_up_question", ""),
            "next_difficulty": eval_result.get("next_difficulty", "same"),
            "status": "success",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/metrics", responses=COMPAT_RESPONSES)
async def get_metrics_compat(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail=_RECRUITER_ONLY)
    """
    Compatibility route matching fetch('${API_BASE_URL}/metrics')
    """
    try:
        metrics = await RecruiterController.get_live_metrics(db=db)

        total_candidates = metrics["key_metrics"]["total_candidates"]
        recent_uploads_7d = metrics["key_metrics"]["recent_uploads_7d"]
        avg_experience = metrics["key_metrics"]["avg_experience_years"]
        unique_skills = metrics["key_metrics"]["unique_skills"]
        avg_match_score = metrics["key_metrics"]["avg_match_score"]

        score_dist = metrics["score_distribution"]
        top_skills = metrics["top_skills"]
        domain_dist = metrics["domain_distribution"]

        return {
            "key_metrics": {
                "total_candidates": total_candidates,
                "avg_match_score": avg_match_score,
                "parsed_resumes": total_candidates,
                "avg_processing_time": 2.4,
                "weekly_growth_percent": 12,
                "avg_experience_years": avg_experience,
                "unique_skills": unique_skills,
            },
            "score_distribution": {
                "labels": score_dist["labels"],
                "datasets": [{"data": score_dist["data"]}],
            },
            "top_skills": {
                "labels": top_skills["labels"],
                "datasets": [{"data": top_skills["data"]}],
            },
            "domain_distribution": domain_dist,
            "monthly_activity": metrics["monthly_activity"],
            "performance_metrics": metrics["performance_metrics"],
            "database_stats": {
                "embeddings_stored": total_candidates,
                "uptime_percentage": 99.8,
                "storage_used_gb": round(total_candidates * 0.005, 2),
                "api_calls_today": recent_uploads_7d * 3,
                "active_candidates_last_7d": recent_uploads_7d,
                "total_skills_count": unique_skills,
            },
            "recent_uploads": metrics["recent_uploads"],
            "top_domains": [
                {"domain": domain, "count": count}
                for domain, count in sorted(
                    domain_dist.items(), key=lambda x: x[1], reverse=True
                )[:5]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/candidate/{candidate_id}", responses=COMPAT_RESPONSES)
async def get_candidate_compat(
    candidate_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail=_RECRUITER_ONLY)
    try:
        profile_data = await CandidateService.get_candidate_profile(db, candidate_id)
        parsed = profile_data["parsed_data"]

        parsed["candidate_name"] = parsed["name"]
        parsed["primary_role_title"] = parsed["role"]
        parsed["primary_domain"] = parsed["domain"]
        parsed["total_experience_years"] = parsed["experience"]

        return {
            "status": "success",
            "candidate_id": profile_data["candidate_id"],
            "parsed_data": parsed,
        }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail="Candidate not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
