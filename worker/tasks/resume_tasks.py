import asyncio
import os

import aiofiles
from sqlalchemy import select

from app.config.database import AsyncSessionLocal
from app.models.candidate import Resume
from app.services.resume import ResumeService
from app.utils.logger import logger

# Maximum time allowed for one full ingestion/persist job (parsing + embedding + Qdrant upsert).
JOB_TIMEOUT_SECONDS = 600

async def _mark_resume_failed(resume_id: int, filepath: str | None, error: str) -> None:
    """
    Opens a FRESH database session (independent of any rolled-back session)
    and sets the resume status to 'FAILED'.
    """
    logger.info(f"[Worker] Opening fresh session to mark resume '{resume_id}' as FAILED.")
    try:
        async with AsyncSessionLocal() as recovery_db:
            stmt = select(Resume).where(Resume.id == resume_id)
            res = await recovery_db.execute(stmt)
            failed_resume = res.scalars().first()
            if failed_resume:
                failed_resume.parse_status = "FAILED"
                failed_resume.parse_error_message = error[:2000]  # Truncate to fit column
                await recovery_db.commit()
                logger.info(f"[Worker] Resume '{resume_id}' successfully marked as FAILED.")

                try:
                    from app.utils.email_helper import send_ingestion_alert
                    await send_ingestion_alert(
                        doc_id=str(resume_id),
                        filename=failed_resume.file_name,
                        status="failed",
                        to_email="admin@resumeintelligence.com",
                        error_message=error
                    )
                except Exception as email_err:
                    logger.error(f"[Worker] Failed to send failure email alert: {email_err}")
    except Exception as recovery_err:
        logger.critical(
            f"[Worker] CRITICAL: Could not mark resume '{resume_id}' as FAILED. "
            f"Manual DB intervention required. Error: {recovery_err}"
        )
    finally:
        # Always clean up the temp file if exists
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"[Worker] Cleaned up temporary file: {filepath}")
            except Exception as clean_err:
                logger.error(f"[Worker] Failed to delete temp file {filepath}: {clean_err}")

async def _run_resume_ingestion(ctx, resume_id: int, filepath: str) -> None:
    """
    Core resume ingestion logic. Reads file bytes, parses, and indexes in Postgres + Qdrant.
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch resume and set status to PENDING/PROCESSING
            stmt = select(Resume).where(Resume.id == resume_id)
            res = await db.execute(stmt)
            db_resume = res.scalars().first()
            if not db_resume:
                logger.error(f"[Worker] Resume record {resume_id} not found in database.")
                return

            db_resume.parse_status = "PROCESSING"
            await db.commit()

            # 2. Read temp file bytes
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"[Worker] Temp file not found: {filepath}")

            async with aiofiles.open(filepath, "rb") as f:
                file_bytes = await f.read()

            # 3. Call core parsing and saving service
            # This handles text extraction, LLM parsing, Postgres records, and Qdrant upsert
            await ResumeService.parse_and_save_resume(
                db=db,
                file_name=db_resume.file_name,
                file_bytes=file_bytes,
                existing_resume_id=resume_id
            )

            # 4. Clean up temporary file on success
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"[Worker] Cleaned up temporary file: {filepath}")

            # 5. Send success email alert
            try:
                from app.utils.email_helper import send_ingestion_alert
                await send_ingestion_alert(
                    doc_id=str(resume_id),
                    filename=db_resume.file_name,
                    status="completed",
                    to_email="admin@resumeintelligence.com"
                )
            except Exception as email_err:
                logger.error(f"[Worker] Failed to send success email alert: {email_err}")

            logger.info(f"[Worker] Ingestion job COMPLETED successfully for Resume ID: {resume_id}")

        except Exception as e:
            await db.rollback()
            raise e

async def _run_candidate_persistence(ctx, resume_id: int, candidate_data: dict) -> None:
    """
    Core candidate persistence logic. Saves pre-parsed candidate details and indexes in Qdrant.
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch resume and set status to PROCESSING
            stmt = select(Resume).where(Resume.id == resume_id)
            res = await db.execute(stmt)
            db_resume = res.scalars().first()
            if not db_resume:
                logger.error(f"[Worker] Resume record {resume_id} not found in database.")
                return

            db_resume.parse_status = "PROCESSING"
            await db.commit()

            # 2. Call service to persist candidate details to DB and Qdrant
            # Inside the service, it commits the changes
            await ResumeService.persist_parsed_candidate(db=db, data=candidate_data)

            # 3. Update status to SUCCESS
            db_resume.parse_status = "SUCCESS"
            await db.commit()

            # 4. Send success email alert
            try:
                from app.utils.email_helper import send_ingestion_alert
                await send_ingestion_alert(
                    doc_id=str(resume_id),
                    filename=db_resume.file_name,
                    status="completed",
                    to_email="admin@resumeintelligence.com"
                )
            except Exception as email_err:
                logger.error(f"[Worker] Failed to send success email alert: {email_err}")

            logger.info(f"[Worker] Persist job COMPLETED successfully for Resume ID: {resume_id}")

        except Exception as e:
            await db.rollback()
            raise e

async def ingest_resume_job(ctx, resume_id: int, filepath: str) -> None:
    """
    ARQ job entry point for resume parsing and vector indexing.
    """
    logger.info(f"[Worker] Starting ingestion job for Resume ID: {resume_id}")
    try:
        await asyncio.wait_for(
            _run_resume_ingestion(ctx, resume_id, filepath),
            timeout=JOB_TIMEOUT_SECONDS
        )
    except TimeoutError:
        error_msg = f"Job exceeded timeout of {JOB_TIMEOUT_SECONDS} seconds."
        logger.error(f"[Worker] TIMEOUT for Resume ID: {resume_id}. {error_msg}")
        await _mark_resume_failed(resume_id, filepath, error_msg)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Worker] FAILED for Resume ID {resume_id}: {error_msg}")
        await _mark_resume_failed(resume_id, filepath, error_msg)
        raise e

async def persist_candidate_job(ctx, resume_id: int, candidate_data: dict) -> None:
    """
    ARQ job entry point for candidate persistence and vector indexing.
    """
    logger.info(f"[Worker] Starting candidate persistence job for Resume ID: {resume_id}")
    try:
        await asyncio.wait_for(
            _run_candidate_persistence(ctx, resume_id, candidate_data),
            timeout=JOB_TIMEOUT_SECONDS
        )
    except TimeoutError:
        error_msg = f"Job exceeded timeout of {JOB_TIMEOUT_SECONDS} seconds."
        logger.error(f"[Worker] TIMEOUT for Resume ID: {resume_id}. {error_msg}")
        await _mark_resume_failed(resume_id, None, error_msg)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Worker] FAILED for Resume ID {resume_id}: {error_msg}")
        await _mark_resume_failed(resume_id, None, error_msg)
        raise e
