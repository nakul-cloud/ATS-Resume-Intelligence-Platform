from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.security import User, get_current_user
from app.controllers.recruiter_controller import RecruiterController
from app.exceptions.custom_exceptions import AppError
from app.schemas.jd import JDEvaluationRequest, JDRewriteRequest
from app.utils.response import error_response, success_response

router = APIRouter()

@router.post("/evaluate")
async def evaluate_job_description(
    request: JDEvaluationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Ranks existing candidates against Job Description text using Qdrant vector-store search
    and scores matching candidate qualifications using dynamic recruiter agents.
    """
    try:
        results = await RecruiterController.evaluate_jd(
            db=db,
            jd_text=request.jd_text,
            domain=request.domain,
            top_k=request.top_k
        )
        response_data = {
            "jd_text": request.jd_text,
            "domain_filter": request.domain,
            "results": results
        }
        return success_response(data=response_data, message="Job description evaluation completed successfully")
    except AppError as e:
        return error_response(message=e.message, code="APP_ERROR", status_code=e.status_code)
    except Exception as e:
        return error_response(
            message="Failed to evaluate job description",
            code="JD_EVALUATION_ERROR",
            status_code=500,
            details=str(e)
        )

@router.post("/normalize")
async def normalize_job_description(
    request: JDRewriteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Stands up a raw job description string and parses it into organized JSON fields.
    """
    try:
        structured_jd = await RecruiterController.normalize_jd(
            db=db,
            jd_text=request.jd_text
        )
        return success_response(data=structured_jd, message="Job description normalized successfully")
    except AppError as e:
        return error_response(message=e.message, code="APP_ERROR", status_code=e.status_code)
    except Exception as e:
        return error_response(
            message="Failed to normalize job description",
            code="JD_NORMALIZATION_ERROR",
            status_code=500,
            details=str(e)
        )
