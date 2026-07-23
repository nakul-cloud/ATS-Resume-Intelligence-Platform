import asyncio
import json
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.resume_parser_agent import parse_resume_text
from app.constants.jobs import STATUS_FAILED, STATUS_PENDING, STATUS_SUCCESS
from app.exceptions.custom_exceptions import AIServiceError, StorageError
from app.models.candidate import Candidate, CandidateSkill, Resume
from app.services.ai.embedder import EmbeddingService
from app.services.ai.vector_store import VectorStore
from app.utils.deduplication import (
    compute_field_diff,
    compute_file_hash,
    compute_skills_diff,
    compute_text_similarity,
)
from app.utils.json_utils import parse_json_list
from app.utils.logger import logger
from app.utils.pdf_extractor import extract_pdf_text
from app.utils.text_builder import build_embedding_text


class ResumeService:
    @classmethod
    async def parse_and_save_resume(
        cls,
        db: AsyncSession,
        file_name: str,
        file_bytes: bytes,
        existing_resume_id: int | None = None,
    ) -> Candidate:
        """
        Parses an uploaded resume PDF, extracts structured candidate data,
        utilizing a three-tiered deduplication strategy to overwrite candidate
        profiles, bypass duplicate LLM calls, and output detailed change logs.
        """
        logger.info(f"Processing resume upload: {file_name}")

        # 1. Tier 1: SHA-256 Hash Matching
        file_hash = compute_file_hash(file_bytes)
        existing_candidate = await cls._process_tier1_hash(db, file_hash)
        if existing_candidate:
            stmt_res = select(Resume).where(Resume.id == existing_candidate.resume_id)
            original_resume = (await db.execute(stmt_res)).scalar_one()
            await cls._link_or_heal_resume(
                db,
                existing_candidate,
                original_resume,
                file_hash,
                original_resume.raw_text or "",
                existing_resume_id,
            )
            await cls._ensure_qdrant_indexed(existing_candidate)
            return existing_candidate

        # 2. Extract plain text from PDF
        resume_text = cls._extract_text_from_pdf(file_bytes, file_name)

        # 3. Tier 2: Plain-Text Similarity Pre-Screening
        matched_candidate = await cls._process_tier2_similarity(
            db, file_hash, resume_text, existing_resume_id
        )
        if matched_candidate:
            await cls._ensure_qdrant_indexed(matched_candidate)
            return matched_candidate

        # Create or fetch existing raw resume record
        db_resume = await cls._get_or_create_resume(
            db, file_name, file_hash, resume_text, existing_resume_id
        )

        try:
            # 4. Call AI Resume Parser Agent (Cache Miss)
            logger.info(
                "Deduplication: Cache MISS. Calling Groq LLM API to parse resume."
            )
            parsed_data = parse_resume_text(resume_text)

            # Extract fields for lookup
            email = parsed_data.get("email")
            phone = parsed_data.get("phone_number")
            name = parsed_data.get("candidate_name")

            candidate = None

            # 5. Tier 3: Identity Lookup (Email / Phone)
            if email:
                stmt = (
                    select(Candidate)
                    .options(selectinload(Candidate.skills))
                    .where(Candidate.email.ilike(email.strip()))
                    .order_by(Candidate.id.desc())
                )
                res = await db.execute(stmt)
                candidate = res.scalars().first()
            if not candidate and name and phone:
                stmt = (
                    select(Candidate)
                    .options(selectinload(Candidate.skills))
                    .where(
                        Candidate.candidate_name.ilike(name.strip()),
                        Candidate.phone_number == phone.strip(),
                    )
                    .order_by(Candidate.id.desc())
                )
                res = await db.execute(stmt)
                candidate = res.scalars().first()

            # Prepare skills list
            new_skills_list = [
                s.get("skill_name", "")
                for s in parsed_data.get("skills", [])
                if s.get("skill_name")
            ]
            new_skills_text = ", ".join(new_skills_list)
            parsed_data["skills_text"] = new_skills_text

            exp_years = parsed_data.get("total_experience_years")
            total_exp = (
                Decimal(str(exp_years)) if exp_years is not None else Decimal("0.0")
            )

            if candidate:
                # Deduplication logic: Check for actual diffs against existing candidate profile
                await cls._update_existing_candidate(
                    db,
                    candidate,
                    db_resume,
                    parsed_data,
                    total_exp,
                    new_skills_list,
                    new_skills_text,
                )
            else:
                # 6. Brand New Candidate (No Identity Match)
                candidate = await cls._create_new_candidate(
                    db,
                    db_resume,
                    parsed_data,
                    total_exp,
                    new_skills_list,
                    new_skills_text,
                )

            # Update raw resume status to SUCCESS
            db_resume.parse_status = STATUS_SUCCESS
            await db.commit()

            # Refresh and load relationships safely
            stmt = (
                select(Candidate)
                .options(selectinload(Candidate.skills))
                .where(Candidate.id == candidate.id)
            )
            res = await db.execute(stmt)
            candidate = res.scalar_one()

            logger.info(
                f"Resume {file_name} successfully parsed, saved, and indexed in Qdrant (candidate_id: {candidate.id})"
            )
            return candidate

        except Exception as e:
            # Revert candidate transaction, mark raw resume as FAILED
            await db.rollback()
            db_resume.parse_status = STATUS_FAILED
            db_resume.parse_error_message = str(e)
            await db.commit()

            logger.error(f"Failed to process and index resume: {e}")
            if isinstance(e, AIServiceError):
                raise
            raise AIServiceError(f"Failed to process and index resume: {e}") from e

    # --- PRIVATE COGNITIVE REDUCTION HELPERS ---

    @classmethod
    async def _process_tier1_hash(
        cls, db: AsyncSession, file_hash: str | None
    ) -> Candidate | None:
        """Handles Tier 1 duplication check based on file hash."""
        if not file_hash:
            return None

        stmt = select(Resume).where(Resume.file_hash == file_hash)
        existing_resume = (await db.execute(stmt)).scalar_one_or_none()
        if not existing_resume:
            return None

        if existing_resume.parse_status == STATUS_SUCCESS:
            stmt = (
                select(Candidate)
                .options(selectinload(Candidate.skills))
                .where(Candidate.resume_id == existing_resume.id)
                .order_by(Candidate.id.desc())
            )
            candidate = (await db.execute(stmt)).scalars().first()
            if candidate:
                logger.info(
                    f"INFO: [Deduplication] Duplicate file hash detected (SHA-256: {file_hash}). Reusing existing Candidate ID {candidate.id} and existing Qdrant embeddings. LLM calls and embedding generation skipped."
                )
                return candidate
            logger.warning(
                f"WARNING: [Self-Healing] Orphan SUCCESS Resume ID {existing_resume.id} has no Candidate record. Deleting orphan to free file_hash unique index."
            )
            await db.delete(existing_resume)
            await db.commit()

        if existing_resume.parse_status == STATUS_PENDING:
            logger.warning(
                f"File hash {file_hash} is currently being processed by another request."
            )
            raise HTTPException(
                status_code=409, detail="This resume is currently being processed."
            )

        if existing_resume.parse_status == STATUS_FAILED:
            logger.info(
                f"Previous parsing attempt for file hash {file_hash} failed. Deleting failed record and re-trying."
            )
            await db.delete(existing_resume)
            await db.commit()

        return None

    @classmethod
    async def get_resume_status(cls, db: AsyncSession, resume_id: int) -> dict:
        """
        Retrieves the asynchronous processing status of a resume by ID.
        """
        stmt = select(Resume).where(Resume.id == resume_id)
        res = await db.execute(stmt)
        resume_record = res.scalars().first()
        if not resume_record:
            raise StorageError(f"Resume with ID {resume_id} not found")

        candidate_id = None
        if resume_record.parse_status == STATUS_SUCCESS:
            stmt_c = (
                select(Candidate.id)
                .where(Candidate.resume_id == resume_record.id)
                .order_by(Candidate.id.desc())
            )
            c_res = await db.execute(stmt_c)
            candidate_id = c_res.scalars().first()

        return {
            "resume_id": resume_record.id,
            "status": resume_record.parse_status,
            "candidate_id": candidate_id,
            "error_message": resume_record.parse_error_message,
        }

    @classmethod
    def _extract_text_from_pdf(cls, file_bytes: bytes, file_name: str) -> str:
        """Extracts plain text from raw PDF bytes."""
        try:
            return extract_pdf_text(file_bytes)
        except Exception as e:
            logger.error(f"PDF extraction failed for {file_name}: {e}")
            raise StorageError(f"Failed to parse PDF file: {e}") from e

    @classmethod
    async def _process_tier2_similarity(
        cls,
        db: AsyncSession,
        file_hash: str | None,
        resume_text: str,
        existing_resume_id: int | None,
    ) -> Candidate | None:
        """Scans successfully parsed resumes for a 98%+ textual matching similarity score."""
        if not resume_text:
            return None

        conditions = [
            Resume.parse_status == STATUS_SUCCESS,
            Resume.raw_text.is_not(None),
        ]
        if existing_resume_id:
            conditions.append(Resume.id != existing_resume_id)

        stmt = (
            select(Resume)
            .where(*conditions)
            .order_by(Resume.created_at.desc())
            .limit(100)
        )
        success_resumes = (await db.execute(stmt)).scalars().all()

        for success_resume in success_resumes:
            compare_text = (
                success_resume.raw_text
                or await cls._build_legacy_fallback_text(db, success_resume.id)
            )
            if not compare_text:
                continue

            sim = compute_text_similarity(resume_text, compare_text)
            if sim >= 0.98:
                stmt = (
                    select(Candidate)
                    .options(selectinload(Candidate.skills))
                    .where(Candidate.resume_id == success_resume.id)
                    .order_by(Candidate.id.desc())
                )
                candidate = (await db.execute(stmt)).scalars().first()
                if candidate:
                    logger.info(
                        f"INFO: [Deduplication] High plain-text similarity ({sim * 100:.1f}%) detected against Resume ID {success_resume.id}. Skipping LLM parsing. Reusing Candidate ID {candidate.id}."
                    )
                    await cls._link_or_heal_resume(
                        db,
                        candidate,
                        success_resume,
                        file_hash,
                        resume_text,
                        existing_resume_id,
                    )
                    return candidate
        return None

    @classmethod
    async def _build_legacy_fallback_text(
        cls, db: AsyncSession, resume_id: int
    ) -> str | None:
        """Builds structured search matching profiles for historical profiles missing raw text."""
        stmt = (
            select(Candidate)
            .options(selectinload(Candidate.skills))
            .where(Candidate.resume_id == resume_id)
            .order_by(Candidate.id.desc())
        )
        candidate = (await db.execute(stmt)).scalars().first()
        if not candidate:
            return None

        skills_str = ", ".join([s.skill_name for s in candidate.skills])
        return (
            f"Name: {candidate.candidate_name or ''}\n"
            f"Email: {candidate.email or ''}\n"
            f"Phone: {candidate.phone_number or ''}\n"
            f"Role: {candidate.primary_role_title or ''}\n"
            f"Domain: {candidate.primary_domain or ''}\n"
            f"Summary: {candidate.summary_text or ''}\n"
            f"Education: {candidate.highest_education or ''}\n"
            f"Experience: {candidate.total_experience_years or 0} years\n"
            f"Skills: {skills_str}"
        )

    @classmethod
    async def _link_or_heal_resume(
        cls,
        db: AsyncSession,
        candidate: Candidate,
        success_resume: Resume,
        file_hash: str | None,
        resume_text: str,
        existing_resume_id: int | None,
    ) -> None:
        """Handles background linking or legacy database metadata self-healing updates."""
        if existing_resume_id:
            stmt_db_res = select(Resume).where(Resume.id == existing_resume_id)
            db_resume = (await db.execute(stmt_db_res)).scalar_one()

            old_resume_id = candidate.resume_id
            if old_resume_id and old_resume_id != db_resume.id:
                stmt_old = select(Resume).where(Resume.id == old_resume_id)
                old_res_rec = (await db.execute(stmt_old)).scalar_one_or_none()
                if old_res_rec:
                    await db.delete(old_res_rec)
                    # Commit the delete immediately to release the unique constraint index
                    await db.commit()

            db_resume.file_hash = file_hash
            db_resume.raw_text = resume_text
            db_resume.parse_status = STATUS_SUCCESS

            candidate.resume = db_resume
            await db.flush()
            await db.commit()
            logger.info(
                f"INFO: [Deduplication] Linked Candidate ID {candidate.id} to new background Resume ID {db_resume.id} and marked SUCCESS."
            )
        else:
            if not success_resume.file_hash or not success_resume.raw_text:
                success_resume.file_hash = file_hash
                success_resume.raw_text = resume_text
                await db.commit()
                logger.info(
                    f"INFO: [Deduplication] Dynamically self-healed file_hash and raw_text for legacy Resume ID {success_resume.id}."
                )

    @classmethod
    async def _ensure_qdrant_indexed(cls, candidate: Candidate) -> None:
        """Ensures the candidate is indexed in Qdrant if they aren't already."""
        try:
            client = VectorStore.get_client()
            existing_points = await asyncio.to_thread(
                client.retrieve,
                collection_name=VectorStore.COLLECTION_NAME,
                ids=[candidate.id],
            )
            if not existing_points:
                logger.info(
                    f"INFO: [Deduplication] Candidate ID {candidate.id} cache hit but missing in Qdrant resumes. Generating vector embeddings and indexing..."
                )

                c_dict = {
                    "primary_role_title": candidate.primary_role_title,
                    "primary_domain": candidate.primary_domain,
                    "total_experience_years": candidate.total_experience_years,
                    "highest_education": candidate.highest_education,
                    "summary_text": candidate.summary_text,
                    "skills_text": candidate.skills_text,
                }
                vector, profile_text = EmbeddingService.encode_candidate(c_dict)

                payload = {
                    "metadata": {
                        "candidate_id": candidate.id,
                        "candidate_name": candidate.candidate_name,
                        "primary_role_title": candidate.primary_role_title,
                        "primary_domain": candidate.primary_domain,
                        "total_experience_years": float(
                            candidate.total_experience_years
                        )
                        if candidate.total_experience_years
                        else 0.0,
                        "skills_text": candidate.skills_text,
                        "summary_text": candidate.summary_text,
                    },
                    "content": profile_text,
                }

                await VectorStore.upsert_chunks(
                    ids=[candidate.id], vectors=[vector], payloads=[payload]
                )
                logger.info(
                    f"INFO: [Deduplication] Successfully indexed Candidate ID {candidate.id} into Qdrant."
                )
            else:
                logger.info(
                    f"INFO: [Deduplication] Candidate ID {candidate.id} already indexed in Qdrant. Skipping embedding generation."
                )
        except Exception as q_err:
            logger.error(f"Error checking/indexing Qdrant on cache hit: {q_err}")

    @classmethod
    async def _get_or_create_resume(
        cls,
        db: AsyncSession,
        file_name: str,
        file_hash: str | None,
        resume_text: str,
        existing_resume_id: int | None,
    ) -> Resume:
        """Fetches the existing Resume record or creates a new one in PENDING status."""
        if existing_resume_id:
            stmt = select(Resume).where(Resume.id == existing_resume_id)
            res = await db.execute(stmt)
            db_resume = res.scalar_one()
            db_resume.file_hash = file_hash
            db_resume.raw_text = resume_text
            await db.commit()
            return db_resume

        # Avoid UniqueViolationError by looking up by file_hash first
        if file_hash:
            stmt_hash = select(Resume).where(Resume.file_hash == file_hash)
            res_hash = await db.execute(stmt_hash)
            existing = res_hash.scalar_one_or_none()
            if existing:
                existing.file_name = file_name
                existing.parse_status = STATUS_PENDING
                existing.raw_text = resume_text
                await db.commit()
                await db.refresh(existing)
                return existing

        db_resume = Resume(
            file_name=file_name,
            parse_status=STATUS_PENDING,
            file_hash=file_hash,
            raw_text=resume_text,
        )
        db.add(db_resume)
        await db.commit()
        await db.refresh(db_resume)
        return db_resume

    @classmethod
    async def _update_existing_candidate(
        cls,
        db: AsyncSession,
        candidate: Candidate,
        db_resume: Resume,
        parsed_data: dict,
        total_exp: Decimal,
        new_skills_list: list[str],
        new_skills_text: str,
    ) -> None:
        """Deduplication logic: Checks for actual diffs and updates existing candidate profile."""
        old_profile_text = build_embedding_text(
            {
                "primary_role_title": candidate.primary_role_title,
                "primary_domain": candidate.primary_domain,
                "total_experience_years": candidate.total_experience_years,
                "highest_education": candidate.highest_education,
                "summary_text": candidate.summary_text,
                "skills_text": candidate.skills_text,
            }
        )

        # Calculate diffs
        field_diffs = compute_field_diff(candidate, parsed_data)
        old_skills = [s.skill_name for s in candidate.skills]
        skills_diff = compute_skills_diff(old_skills, new_skills_list)

        has_changes = len(field_diffs) > 0 or skills_diff["changed"]

        if has_changes:
            cls._log_change_diffs(
                candidate.id,
                parsed_data.get("candidate_name") or "",
                field_diffs,
                skills_diff,
            )

            # Overwrite fields
            candidate.candidate_name = parsed_data.get("candidate_name")
            candidate.email = parsed_data.get("email")
            candidate.phone_number = parsed_data.get("phone_number")
            candidate.primary_role_title = parsed_data.get("primary_role_title")
            candidate.primary_domain = parsed_data.get("primary_domain")
            candidate.total_experience_years = total_exp
            candidate.highest_education = parsed_data.get("highest_education")
            candidate.summary_text = parsed_data.get("summary_text")
            candidate.skills_text = new_skills_text
            candidate.projects_json = json.dumps(parsed_data.get("projects", []))
            candidate.accomplishments_json = json.dumps(
                parsed_data.get("accomplishments", [])
            )
            candidate.hobbies_json = json.dumps(parsed_data.get("hobbies", []))
            candidate.work_experience_json = json.dumps(
                parsed_data.get("work_experience", [])
            )
            await db.flush()

            # Replace skills relations
            await db.execute(
                delete(CandidateSkill).where(
                    CandidateSkill.candidate_id == candidate.id
                )
            )
            for skill_name in new_skills_list:
                db_skill = CandidateSkill(
                    candidate_id=candidate.id, skill_name=skill_name
                )
                db.add(db_skill)

            # Vector Re-indexing
            c_dict = {
                "primary_role_title": candidate.primary_role_title,
                "primary_domain": candidate.primary_domain,
                "total_experience_years": candidate.total_experience_years,
                "highest_education": candidate.highest_education,
                "summary_text": candidate.summary_text,
                "skills_text": candidate.skills_text,
            }
            profile_text = build_embedding_text(c_dict)

            if profile_text != old_profile_text:
                vector, profile_text = EmbeddingService.encode_candidate(c_dict)
                payload = {
                    "metadata": {
                        "candidate_id": candidate.id,
                        "candidate_name": candidate.candidate_name,
                        "primary_role_title": candidate.primary_role_title,
                        "primary_domain": candidate.primary_domain,
                        "total_experience_years": float(
                            candidate.total_experience_years
                        )
                        if candidate.total_experience_years
                        else 0.0,
                        "skills_text": candidate.skills_text,
                        "summary_text": candidate.summary_text,
                    },
                    "content": profile_text,
                }
                await VectorStore.upsert_chunks(
                    ids=[candidate.id], vectors=[vector], payloads=[payload]
                )
                logger.info(
                    f"INFO: [Deduplication] Qdrant vector point ID {candidate.id} overwritten with updated embedding."
                )
        else:
            logger.info(
                f"INFO: [Deduplication] Candidate ID {candidate.id} data is identical. Skipping database update and Qdrant re-indexing."
            )

        # Link candidate to the new resume and clean up the old resume to avoid orphans
        old_resume_id = candidate.resume_id
        candidate.resume = db_resume
        await db.flush()
        await cls._cleanup_old_resume(db, old_resume_id, db_resume.id)

    @classmethod
    async def _create_new_candidate(
        cls,
        db: AsyncSession,
        db_resume: Resume,
        parsed_data: dict,
        total_exp: Decimal,
        new_skills_list: list[str],
        new_skills_text: str,
    ) -> Candidate:
        """Creates a brand new candidate record and vector indexes them in Qdrant."""
        candidate = Candidate(
            resume_id=db_resume.id,
            candidate_name=parsed_data.get("candidate_name"),
            email=parsed_data.get("email"),
            phone_number=parsed_data.get("phone_number"),
            primary_role_title=parsed_data.get("primary_role_title"),
            primary_domain=parsed_data.get("primary_domain"),
            total_experience_years=total_exp,
            highest_education=parsed_data.get("highest_education"),
            summary_text=parsed_data.get("summary_text"),
            skills_text=new_skills_text,
            projects_json=json.dumps(parsed_data.get("projects", [])),
            accomplishments_json=json.dumps(parsed_data.get("accomplishments", [])),
            hobbies_json=json.dumps(parsed_data.get("hobbies", [])),
            work_experience_json=json.dumps(parsed_data.get("work_experience", [])),
        )
        db.add(candidate)
        await db.flush()

        # Save individual skills
        for skill_name in new_skills_list:
            db_skill = CandidateSkill(candidate_id=candidate.id, skill_name=skill_name)
            db.add(db_skill)

        # Generate search vector
        c_dict = {
            "primary_role_title": candidate.primary_role_title,
            "primary_domain": candidate.primary_domain,
            "total_experience_years": candidate.total_experience_years,
            "highest_education": candidate.highest_education,
            "summary_text": candidate.summary_text,
            "skills_text": candidate.skills_text,
        }
        vector, profile_text = EmbeddingService.encode_candidate(c_dict)

        payload = {
            "metadata": {
                "candidate_id": candidate.id,
                "candidate_name": candidate.candidate_name,
                "primary_role_title": candidate.primary_role_title,
                "primary_domain": candidate.primary_domain,
                "total_experience_years": float(candidate.total_experience_years)
                if candidate.total_experience_years
                else 0.0,
                "skills_text": candidate.skills_text,
                "summary_text": candidate.summary_text,
            },
            "content": profile_text,
        }

        await VectorStore.upsert_chunks(
            ids=[candidate.id], vectors=[vector], payloads=[payload]
        )
        return candidate

    @classmethod
    def _log_change_diffs(
        cls,
        candidate_id: int,
        candidate_name: str,
        field_diffs: dict,
        skills_diff: dict,
    ) -> None:
        """Helper to print candidate profile changes in logs."""
        log_msg = f"INFO: [Deduplication] Identity match found for candidate '{candidate_name}' (ID: {candidate_id}). Diffs detected:\n"
        for col, val in field_diffs.items():
            log_msg += f"  - {col}: '{val['old']}' → '{val['new']}'\n"
        if skills_diff.get("added"):
            log_msg += f"  - skills_added: {skills_diff['added']}\n"
        if skills_diff.get("removed"):
            log_msg += f"  - skills_removed: {skills_diff['removed']}\n"
        logger.info(log_msg)

    @classmethod
    async def _cleanup_old_resume(
        cls, db: AsyncSession, old_resume_id: int | None, new_resume_id: int
    ) -> None:
        """Safely cleans up the old resume to avoid orphans when linking a new resume."""
        if old_resume_id and old_resume_id != new_resume_id:
            stmt_del_res = select(Resume).where(Resume.id == old_resume_id)
            res_del_res = await db.execute(stmt_del_res)
            old_resume_rec = res_del_res.scalars().first()
            if old_resume_rec:
                old_resume_rec.candidate = None
                await db.delete(old_resume_rec)

    @classmethod
    @classmethod
    async def parse_resume_session(
        cls, file_name: str, file_bytes: bytes, db: AsyncSession | None = None
    ) -> dict:
        """
        Parses an uploaded resume PDF in-memory, completely bypassing database
        persistence and vector stores. If db is provided and the file hash already
        exists, retrieves the parsed details from database cache.
        """
        from app.services.candidate_session import CandidateSessionService
        return await CandidateSessionService.parse_resume_session(
            file_name=file_name, file_bytes=file_bytes, db=db
        )

    @classmethod
    async def persist_parsed_candidate(
        cls, db: AsyncSession, data: dict, async_embed: bool = False
    ) -> Candidate:
        """
        Saves a pre-parsed candidate profile directly to Postgres and indexes in Qdrant,
        using standard deduplication to update existing records if emails match.
        """
        from app.services.candidate_persist import CandidatePersistService
        return await CandidatePersistService.persist_parsed_candidate(
            db=db, data=data, async_embed=async_embed
        )
