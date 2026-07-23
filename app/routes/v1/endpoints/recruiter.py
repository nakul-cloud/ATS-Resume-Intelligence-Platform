from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.security import User, get_current_user
from app.controllers.recruiter_controller import RecruiterController
from app.exceptions.custom_exceptions import AppError
from app.utils.response import error_response, success_response

router = APIRouter()

@router.get("/metrics/live")
async def get_live_dashboard_metrics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Returns live database candidate distributions, evaluation indicators,
    and monthly trends to feed the recruiter dashboard charts.
    """
    try:
        metrics = await RecruiterController.get_live_metrics(db=db)
        return success_response(data=metrics, message="Live dashboard metrics retrieved successfully")
    except AppError as e:
        return error_response(message=e.message, code="APP_ERROR", status_code=e.status_code)
    except Exception as e:
        return error_response(
            message="Failed to retrieve dashboard metrics",
            code="METRICS_RETRIEVAL_ERROR",
            status_code=500,
            details=str(e)
        )
