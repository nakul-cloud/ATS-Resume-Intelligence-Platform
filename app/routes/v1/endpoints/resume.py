from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.security import get_current_user, User
from app.controllers.resume_controller import ResumeController

router = APIRouter()

@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a candidate resume PDF. Passes call directly to ResumeController
    which manages the HTTP status codes, validation, and Pydantic schema serialization.
    """
    return await ResumeController.upload_resume(db=db, file=file)
