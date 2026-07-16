from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.security import User, get_current_user
from app.controllers.interview_controller import InterviewController
from app.exceptions.custom_exceptions import AppError
from app.schemas.interview import (
    InterviewAnswerSubmitRequest,
    InterviewSessionCreateRequest,
)
from app.utils.response import error_response, success_response

router = APIRouter()

@router.post("/session")
async def start_interview_session(
    request: InterviewSessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Starts a new dynamic interview session for a candidate, generating the first question.
    """
    try:
        response_data = await InterviewController.start_session(
            db=db,
            candidate_id=request.candidate_id,
            evaluation_id=request.evaluation_id
        )
        return success_response(data=response_data, message="Interview session started successfully", status_code=211)
    except AppError as e:
        return error_response(message=e.message, code="APP_ERROR", status_code=e.status_code)
    except Exception as e:
        return error_response(
            message="Failed to start interview session",
            code="INTERVIEW_START_ERROR",
            status_code=500,
            details=str(e)
        )

@router.post("/answer")
async def submit_interview_answer(
    request: InterviewAnswerSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits candidate answer, returns score feedback and next question (if active).
    """
    try:
        eval_result = await InterviewController.submit_answer(
            db=db,
            question_id=request.question_id,
            answer_text=request.answer_text
        )
        return success_response(data=eval_result, message="Answer evaluated successfully")
    except AppError as e:
        return error_response(message=e.message, code="APP_ERROR", status_code=e.status_code)
    except Exception as e:
        return error_response(
            message="Failed to evaluate interview answer",
            code="INTERVIEW_EVALUATION_ERROR",
            status_code=500,
            details=str(e)
        )
