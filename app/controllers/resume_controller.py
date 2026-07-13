from fastapi import UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.resume import ResumeService
from app.schemas.candidate import CandidateParsedData
from app.exceptions.custom_exceptions import AppError, ValidationError
from app.utils.logger import logger
from app.utils.response import success_response, error_response

class ResumeController:
    @classmethod
    async def upload_resume(cls, db: AsyncSession, file: UploadFile) -> JSONResponse:
        """
        Manages the HTTP request for uploading and parsing a resume PDF.
        Validates file types, executes the parsing pipeline, and returns the appropriate HTTP status codes.
        """
        logger.info("ResumeController: Received resume upload request.")
        
        # 1. HTTP Input Validation
        if not file.filename.lower().endswith(".pdf"):
            logger.warning("ResumeController: Rejected upload due to invalid file type.")
            return error_response(
                message="Only PDF files are supported",
                code="INVALID_FILE_TYPE",
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 2. Call Service Method
            file_bytes = await file.read()
            candidate = await ResumeService.parse_and_save_resume(
                db=db,
                file_name=file.filename,
                file_bytes=file_bytes
            )
            
            # 3. Map Pydantic structures for serialization safety
            import json
            work_exp = json.loads(candidate.work_experience_json) if candidate.work_experience_json else []
            projects = json.loads(candidate.projects_json) if candidate.projects_json else []
            accomplishments = json.loads(candidate.accomplishments_json) if candidate.accomplishments_json else []
            hobbies = json.loads(candidate.hobbies_json) if candidate.hobbies_json else []

            parsed_data = CandidateParsedData(
                candidate_name=candidate.candidate_name,
                email=candidate.email,
                phone_number=candidate.phone_number,
                primary_role_title=candidate.primary_role_title,
                primary_domain=candidate.primary_domain,
                total_experience_years=float(candidate.total_experience_years) if candidate.total_experience_years else 0.0,
                highest_education=candidate.highest_education,
                summary_text=candidate.summary_text,
                skills=[{"skill_name": s.skill_name} for s in candidate.skills],
                work_experience=work_exp,
                projects=projects,
                accomplishments=accomplishments,
                hobbies=hobbies
            )
            
            response_payload = {
                "status": "success",
                "candidate_id": candidate.id,
                "parsed_data": parsed_data.dict(),
                "message": "Resume successfully uploaded, parsed, and indexed."
            }
            
            # 4. Map HTTP Status Code (201 Created)
            return success_response(
                data=response_payload,
                message="Resume processed successfully",
                status_code=status.HTTP_201_CREATED
            )

        except AppError as e:
            logger.error(f"ResumeController: Application exception caught: {e.message}")
            return error_response(
                message=e.message,
                code="APP_ERROR",
                status_code=e.status_code
            )
        except Exception as e:
            logger.error(f"ResumeController: Unexpected exception caught: {str(e)}")
            return error_response(
                message="An unexpected error occurred during resume processing",
                code="RESUME_PROCESSING_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details=str(e)
            )
