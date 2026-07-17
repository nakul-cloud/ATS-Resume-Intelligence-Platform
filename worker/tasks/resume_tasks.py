from __future__ import annotations

import asyncio
import os
from typing import Any

import aiofiles
from sqlalchemy import select

from app.config.database import AsyncSessionLocal
from app.config.settings import settings
from app.constants.jobs import (
    ALERT_COMPLETED,
    ALERT_FAILED,
    JOB_TIMEOUT_SECONDS,
    MAX_ERROR_LENGTH,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STATUS_SUCCESS,
)
from app.models.candidate import Resume
from app.services.resume import ResumeService
from app.utils.logger import logger


def _safe_remove_file(filepath: str | None) -> None:
    """Safely cleans up temporary files from disk."""
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
            logger.info(f"[Worker] Cleaned up temporary file: {filepath}")
        except Exception as clean_err:
            logger.error(f"[Worker] Failed to delete temp file {filepath}: {clean_err}")


async def _send_worker_alert(resume_id: int, filename: str, status: str, error_message: str | None = None) -> None:
    """Consolidates the duplicated notification logic into a clean reusable helper."""
    try:
        from app.utils.email_helper import send_ingestion_alert
        await send_ingestion_alert(
            doc_id=str(resume_id),
            filename=filename,
            status=status,
            to_email=settings.mail_admin_email,
            error_message=error_message
        )
    except Exception as email_err:
        logger.error(f"[Worker] Failed to send {status} email alert: {email_err}")


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
                failed_resume.parse_status = STATUS_FAILED
                failed_resume.parse_error_message = error[:MAX_ERROR_LENGTH]
                await recovery_db.commit()
                logger.info(f"[Worker] Resume '{resume_id}' successfully marked as FAILED.")

                await _send_worker_alert(
                    resume_id=resume_id,
                    filename=failed_resume.file_name,
                    status=ALERT_FAILED,
                    error_message=error
                )
    except Exception as recovery_err:
        logger.critical(
            f"[Worker] CRITICAL: Could not mark resume '{resume_id}' as FAILED. "
            f"Manual DB intervention required. Error: {recovery_err}"
        )
    finally:
        _safe_remove_file(filepath)


async def _run_resume_ingestion(_ctx: Any, resume_id: int, filepath: str) -> None:
    """
    Core resume ingestion logic. Reads file bytes, parses, and indexes in Postgres + Qdrant.
    """
    async with AsyncSessionLocal() as db:
        try:
            stmt = select(Resume).where(Resume.id == resume_id)
            res = await db.execute(stmt)
            db_resume = res.scalars().first()
            if not db_resume:
                logger.error(f"[Worker] Resume record {resume_id} not found in database.")
                return

            db_resume.parse_status = STATUS_PROCESSING
            await db.commit()

            if not os.path.exists(filepath):
                raise FileNotFoundError(f"[Worker] Temp file not found: {filepath}")

            async with aiofiles.open(filepath, "rb") as f:
                file_bytes = await f.read()

            await ResumeService.parse_and_save_resume(
                db=db,
                file_name=db_resume.file_name,
                file_bytes=file_bytes,
                existing_resume_id=resume_id
            )

            _safe_remove_file(filepath)
            await _send_worker_alert(resume_id, db_resume.file_name, ALERT_COMPLETED)
            logger.info(f"[Worker] Ingestion job COMPLETED successfully for Resume ID: {resume_id}")

        except Exception as e:
            await db.rollback()
            raise e


async def _run_candidate_persistence(_ctx: Any, resume_id: int, candidate_data: dict) -> None:
    """
    Core candidate persistence logic. Saves pre-parsed candidate details and indexes in Qdrant.
    """
    async with AsyncSessionLocal() as db:
        try:
            stmt = select(Resume).where(Resume.id == resume_id)
            res = await db.execute(stmt)
            db_resume = res.scalars().first()
            if not db_resume:
                logger.error(f"[Worker] Resume record {resume_id} not found in database.")
                return

            db_resume.parse_status = STATUS_PROCESSING
            await db.commit()

            await ResumeService.persist_parsed_candidate(db=db, data=candidate_data)

            db_resume.parse_status = STATUS_SUCCESS
            await db.commit()

            await _send_worker_alert(resume_id, db_resume.file_name, ALERT_COMPLETED)
            logger.info(f"[Worker] Persist job COMPLETED successfully for Resume ID: {resume_id}")

        except Exception as e:
            await db.rollback()
            raise e


async def ingest_resume_job(_ctx: Any, resume_id: int, filepath: str) -> None:
    """
    ARQ job entry point for resume parsing and vector indexing.
    """
    logger.info(f"[Worker] Starting ingestion job for Resume ID: {resume_id}")
    try:
        await asyncio.wait_for(
            _run_resume_ingestion(_ctx, resume_id, filepath),
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


async def persist_candidate_job(_ctx: Any, resume_id: int, candidate_data: dict) -> None:
    """
    ARQ job entry point for candidate persistence and vector indexing.
    """
    logger.info(f"[Worker] Starting candidate persistence job for Resume ID: {resume_id}")
    try:
        await asyncio.wait_for(
            _run_candidate_persistence(_ctx, resume_id, candidate_data),
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
