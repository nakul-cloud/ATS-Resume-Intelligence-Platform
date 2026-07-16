from fastapi import UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.custom_exceptions import AppError
from app.utils.logger import logger
from app.utils.response import error_response, success_response


class ResumeController:
    @classmethod
    async def upload_resume(cls, db: AsyncSession, file: UploadFile) -> JSONResponse:
        """
        Manages the HTTP request for uploading and parsing a resume PDF.
        Validates file types, inserts a PENDING Resume record, enqueues the parsing job,
        and returns a 202 Accepted response.
        """
        import os
        import uuid

        import aiofiles

        from app.models.candidate import Resume

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
            # 2. Read file bytes and save to a temporary folder
            file_bytes = await file.read()
            temp_dir = os.path.join(os.getcwd(), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            temp_filename = f"{uuid.uuid4()}_{file.filename}"
            temp_filepath = os.path.join(temp_dir, temp_filename)

            async with aiofiles.open(temp_filepath, "wb") as f:
                await f.write(file_bytes)

            # 3. Create a raw resume record in database with status PENDING
            db_resume = Resume(
                file_name=file.filename,
                parse_status="PENDING",
                raw_text=""
            )
            db.add(db_resume)
            await db.commit()
            await db.refresh(db_resume)

            # 4. Enqueue the parsing job via ArqQueueService
            from app.services.arq_queue import ArqQueueService
            await ArqQueueService.enqueue_job("ingest_resume_job", db_resume.id, temp_filepath)

            response_payload = {
                "status": "PENDING",
                "resume_id": db_resume.id,
                "message": "Resume successfully uploaded. Processing in background."
            }

            # 5. Return HTTP Status Code (202 Accepted)
            return success_response(
                data=response_payload,
                message="Resume uploaded successfully",
                status_code=status.HTTP_202_ACCEPTED
            )

        except AppError as e:
            logger.error(f"ResumeController: Application exception caught: {e.message}")
            return error_response(
                message=e.message,
                code="APP_ERROR",
                status_code=e.status_code
            )
        except Exception as e:
            logger.error(f"ResumeController: Unexpected exception caught: {e!s}")
            return error_response(
                message="An unexpected error occurred during resume processing",
                code="RESUME_PROCESSING_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details=str(e)
            )
