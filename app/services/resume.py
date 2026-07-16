import asyncio
import json
from decimal import Decimal

from fastapi import HTTPException
from sentence_transformers import SentenceTransformer
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.resume_parser_agent import parse_resume_text
from app.config.settings import settings
from app.exceptions.custom_exceptions import AIServiceError, StorageError
from app.models.candidate import Candidate, CandidateSkill, Resume
from app.services.ai.vector_store import VectorStore
from app.utils.deduplication import (
    compute_field_diff,
    compute_file_hash,
    compute_skills_diff,
    compute_text_similarity,
)
from app.utils.logger import logger
from app.utils.pdf_extractor import extract_pdf_text
from app.utils.text_builder import build_embedding_text


class ResumeService:
    _model = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """Lazily loads the SentenceTransformer embedding model."""
        if cls._model is None:
            logger.info(f"Loading SentenceTransformer model ({settings.embedding_model_name})...")
            cls._model = SentenceTransformer(settings.embedding_model_name)
        return cls._model

    @classmethod
    async def parse_and_save_resume(cls, db: AsyncSession, file_name: str, file_bytes: bytes, existing_resume_id: int | None = None) -> Candidate:
        """
        Parses an uploaded resume PDF, extracts structured candidate data,
        utilizing a three-tiered deduplication strategy to overwrite candidate
        profiles, bypass duplicate LLM calls, and output detailed change logs.
        """
        logger.info(f"Processing resume upload: {file_name}")

        # 1. Tier 1: Calculate and check SHA-256 File Hash
        file_hash = compute_file_hash(file_bytes)
        if file_hash:
            stmt = select(Resume).where(Resume.file_hash == file_hash)
            res = await db.execute(stmt)
            existing_resume = res.scalar_one_or_none()

            if existing_resume:
                if existing_resume.parse_status == "SUCCESS":
                    # Fetch linked candidate
                    stmt = select(Candidate).options(selectinload(Candidate.skills)).where(Candidate.resume_id == existing_resume.id).order_by(Candidate.id.desc())
                    cand_res = await db.execute(stmt)
                    candidate = cand_res.scalars().first()
                    if candidate:
                        logger.info(f"INFO: [Deduplication] Duplicate file hash detected (SHA-256: {file_hash}). Reusing existing Candidate ID {candidate.id} and existing Qdrant embeddings. LLM calls and embedding generation skipped.")
                        return candidate
                elif existing_resume.parse_status == "PENDING":
                    logger.warning(f"File hash {file_hash} is currently being processed by another request.")
                    raise HTTPException(status_code=409, detail="This resume is currently being processed.")
                elif existing_resume.parse_status == "FAILED":
                    logger.info(f"Previous parsing attempt for file hash {file_hash} failed. Deleting failed record and re-trying.")
                    await db.delete(existing_resume)
                    await db.commit()

        # 2. Extract plain text from PDF
        try:
            resume_text = extract_pdf_text(file_bytes)
        except Exception as e:
            logger.error(f"PDF extraction failed for {file_name}: {e}")
            raise StorageError(f"Failed to parse PDF file: {e}") from e

        # 3. Tier 2: Plain-Text Similarity Pre-Screening
        if resume_text:
            stmt = select(Resume).where(Resume.parse_status == "SUCCESS")
            res = await db.execute(stmt)
            success_resumes = res.scalars().all()

            for success_resume in success_resumes:
                compare_text = success_resume.raw_text

                # Dynamic fallback for historic restore records missing raw_text
                if not compare_text:
                    stmt = select(Candidate).options(selectinload(Candidate.skills)).where(Candidate.resume_id == success_resume.id).order_by(Candidate.id.desc())
                    cand_res = await db.execute(stmt)
                    candidate = cand_res.scalars().first()
                    if candidate:
                        skills_str = ", ".join([s.skill_name for s in candidate.skills])
                        compare_text = (
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

                if compare_text:
                    sim = compute_text_similarity(resume_text, compare_text)
                    if sim >= 0.98:
                        stmt = select(Candidate).options(selectinload(Candidate.skills)).where(Candidate.resume_id == success_resume.id).order_by(Candidate.id.desc())
                        cand_res = await db.execute(stmt)
                        candidate = cand_res.scalars().first()
                        if candidate:
                            logger.info(f"INFO: [Deduplication] High plain-text similarity ({sim * 100:.1f}%) detected against Resume ID {success_resume.id}. Skipping LLM parsing. Reusing Candidate ID {candidate.id}.")

                            # Self-healing & Worker Integration: Link candidate to new resume if background upload
                            if existing_resume_id:
                                stmt_db_res = select(Resume).where(Resume.id == existing_resume_id)
                                res_db_res = await db.execute(stmt_db_res)
                                db_resume = res_db_res.scalar_one()

                                db_resume.file_hash = file_hash
                                db_resume.raw_text = resume_text
                                db_resume.parse_status = "SUCCESS"

                                old_resume_id = candidate.resume_id
                                candidate.resume = db_resume
                                await db.flush()

                                # Safely clean up the old resume without triggering delete-orphan cascade
                                if old_resume_id and old_resume_id != db_resume.id:
                                    stmt_del_res = select(Resume).where(Resume.id == old_resume_id)
                                    res_del_res = await db.execute(stmt_del_res)
                                    old_resume_rec = res_del_res.scalars().first()
                                    if old_resume_rec:
                                        old_resume_rec.candidate = None
                                        await db.delete(old_resume_rec)
                                await db.commit()
                                logger.info(f"INFO: [Deduplication] Linked Candidate ID {candidate.id} to new background Resume ID {db_resume.id} and marked SUCCESS.")
                            else:
                                if not success_resume.file_hash or not success_resume.raw_text:
                                    success_resume.file_hash = file_hash
                                    success_resume.raw_text = resume_text
                                    await db.commit()
                                    logger.info(f"INFO: [Deduplication] Dynamically self-healed file_hash and raw_text for legacy Resume ID {success_resume.id}.")

                            # Ensure the candidate is indexed in Qdrant if they aren't already
                            try:
                                client = VectorStore.get_client()
                                existing_points = await asyncio.to_thread(
                                    client.retrieve,
                                    collection_name=VectorStore.COLLECTION_NAME,
                                    ids=[candidate.id]
                                )
                                if not existing_points:
                                    logger.info(f"INFO: [Deduplication] Candidate ID {candidate.id} cache hit but missing in Qdrant resumes. Generating vector embeddings and indexing...")

                                    c_dict = {
                                        "primary_role_title": candidate.primary_role_title,
                                        "primary_domain": candidate.primary_domain,
                                        "total_experience_years": candidate.total_experience_years,
                                        "highest_education": candidate.highest_education,
                                        "summary_text": candidate.summary_text,
                                        "skills_text": candidate.skills_text,
                                    }
                                    profile_text = build_embedding_text(c_dict)
                                    model = cls.get_model()
                                    vector = model.encode(profile_text).tolist()

                                    payload = {
                                        "metadata": {
                                            "candidate_id": candidate.id,
                                            "candidate_name": candidate.candidate_name,
                                            "primary_role_title": candidate.primary_role_title,
                                            "primary_domain": candidate.primary_domain,
                                            "total_experience_years": float(candidate.total_experience_years) if candidate.total_experience_years else 0.0,
                                            "skills_text": candidate.skills_text,
                                            "summary_text": candidate.summary_text,
                                        },
                                        "content": profile_text,
                                    }

                                    await VectorStore.upsert_chunks(
                                        ids=[candidate.id],
                                        vectors=[vector],
                                        payloads=[payload]
                                    )
                                    logger.info(f"INFO: [Deduplication] Successfully indexed Candidate ID {candidate.id} into Qdrant.")
                                else:
                                    logger.info(f"INFO: [Deduplication] Candidate ID {candidate.id} already indexed in Qdrant. Skipping embedding generation.")
                            except Exception as q_err:
                                logger.error(f"Error checking/indexing Qdrant on cache hit: {q_err}")

                            return candidate

        # Create or fetch existing raw resume record
        if existing_resume_id:
            stmt = select(Resume).where(Resume.id == existing_resume_id)
            res = await db.execute(stmt)
            db_resume = res.scalar_one()
            db_resume.file_hash = file_hash
            db_resume.raw_text = resume_text
        else:
            db_resume = Resume(file_name=file_name, parse_status="PENDING", file_hash=file_hash, raw_text=resume_text)
            db.add(db_resume)
            await db.commit()
            await db.refresh(db_resume)

        try:
            # 4. Call AI Resume Parser Agent (Cache Miss)
            logger.info("Deduplication: Cache MISS. Calling Groq LLM API to parse resume.")
            parsed_data = parse_resume_text(resume_text)

            # Extract fields for lookup
            email = parsed_data.get("email")
            phone = parsed_data.get("phone_number")
            name = parsed_data.get("candidate_name")

            candidate = None
            is_overwrite = False

            # 5. Tier 3: Identity Lookup (Email / Phone)
            if email:
                stmt = select(Candidate).options(selectinload(Candidate.skills)).where(Candidate.email.ilike(email.strip())).order_by(Candidate.id.desc())
                res = await db.execute(stmt)
                candidate = res.scalars().first()
            if not candidate and name and phone:
                stmt = select(Candidate).options(selectinload(Candidate.skills)).where(
                    Candidate.candidate_name.ilike(name.strip()),
                    Candidate.phone_number == phone.strip()
                ).order_by(Candidate.id.desc())
                res = await db.execute(stmt)
                candidate = res.scalars().first()

            # Prepare skills list
            new_skills_list = [s.get("skill_name", "") for s in parsed_data.get("skills", []) if s.get("skill_name")]
            new_skills_text = ", ".join(new_skills_list)
            parsed_data["skills_text"] = new_skills_text

            exp_years = parsed_data.get("total_experience_years")
            total_exp = Decimal(str(exp_years)) if exp_years is not None else Decimal("0.0")

            if candidate:
                # Identity Match: Overwrite/Update Profile
                is_overwrite = True
                logger.info(f"INFO: [Deduplication] Candidate ID {candidate.id} matched by identity (Email: {candidate.email}). Running field comparisons.")

                # Build old profile text before we update any fields in memory
                old_profile_text = build_embedding_text({
                    "primary_role_title": candidate.primary_role_title or "",
                    "primary_domain": candidate.primary_domain or "",
                    "total_experience_years": candidate.total_experience_years or Decimal("0.0"),
                    "highest_education": candidate.highest_education or "",
                    "summary_text": candidate.summary_text or "",
                    "skills_text": candidate.skills_text or ""
                })

                # Compare old values vs new parsed values
                diff = compute_field_diff(candidate, parsed_data)
                old_skills = [s.skill_name for s in candidate.skills]
                skills_diff = compute_skills_diff(old_skills, new_skills_list)

                has_changes = len(diff) > 0 or skills_diff["changed"]

                if has_changes:
                    # Print change diffs in logs
                    log_msg = f"INFO: [Deduplication] Updating candidate ID {candidate.id}. Changes detected:\n"
                    for col, val in diff.items():
                        log_msg += f"  - {col}: '{val['old']}' → '{val['new']}'\n"
                    if skills_diff["added"]:
                        log_msg += f"  - skills_added: {skills_diff['added']}\n"
                    if skills_diff["removed"]:
                        log_msg += f"  - skills_removed: {skills_diff['removed']}\n"
                    logger.info(log_msg)

                    # Apply updates to Candidate
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
                    candidate.accomplishments_json = json.dumps(parsed_data.get("accomplishments", []))
                    candidate.hobbies_json = json.dumps(parsed_data.get("hobbies", []))
                    candidate.work_experience_json = json.dumps(parsed_data.get("work_experience", []))

                    # Replace skills relations
                    await db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == candidate.id))
                    for skill_name in new_skills_list:
                        db_skill = CandidateSkill(candidate_id=candidate.id, skill_name=skill_name)
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
                        model = cls.get_model()
                        vector = model.encode(profile_text).tolist()
                        payload = {
                            "metadata": {
                                "candidate_id": candidate.id,
                                "candidate_name": candidate.candidate_name,
                                "primary_role_title": candidate.primary_role_title,
                                "primary_domain": candidate.primary_domain,
                                "total_experience_years": float(candidate.total_experience_years) if candidate.total_experience_years else 0.0,
                                "skills_text": candidate.skills_text,
                                "summary_text": candidate.summary_text,
                            },
                            "content": profile_text,
                        }
                        await VectorStore.upsert_chunks(
                            ids=[candidate.id],
                            vectors=[vector],
                            payloads=[payload]
                        )
                        logger.info(f"INFO: [Deduplication] Qdrant vector point ID {candidate.id} overwritten with updated embedding.")
                else:
                    logger.info(f"INFO: [Deduplication] Candidate ID {candidate.id} data is identical. Skipping database update and Qdrant re-indexing.")

                # Link candidate to the new resume and clean up the old resume to avoid orphans
                old_resume_id = candidate.resume_id
                candidate.resume = db_resume
                await db.flush()

                if old_resume_id and old_resume_id != db_resume.id:
                    stmt_del_res = select(Resume).where(Resume.id == old_resume_id)
                    res_del_res = await db.execute(stmt_del_res)
                    old_resume_rec = res_del_res.scalars().first()
                    if old_resume_rec:
                        old_resume_rec.candidate = None
                        await db.delete(old_resume_rec)

            else:
                # 6. Brand New Candidate (No Identity Match)
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
                    work_experience_json=json.dumps(parsed_data.get("work_experience", []))
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
                profile_text = build_embedding_text(c_dict)
                model = cls.get_model()
                vector = model.encode(profile_text).tolist()

                payload = {
                    "metadata": {
                        "candidate_id": candidate.id,
                        "candidate_name": candidate.candidate_name,
                        "primary_role_title": candidate.primary_role_title,
                        "primary_domain": candidate.primary_domain,
                        "total_experience_years": float(candidate.total_experience_years) if candidate.total_experience_years else 0.0,
                        "skills_text": candidate.skills_text,
                        "summary_text": candidate.summary_text,
                    },
                    "content": profile_text,
                }

                await VectorStore.upsert_chunks(
                    ids=[candidate.id],
                    vectors=[vector],
                    payloads=[payload]
                )

            # Update raw resume status to SUCCESS
            db_resume.parse_status = "SUCCESS"
            await db.commit()

            # Refresh and load relationships safely
            stmt = select(Candidate).options(selectinload(Candidate.skills)).where(Candidate.id == candidate.id)
            res = await db.execute(stmt)
            candidate = res.scalar_one()

            if is_overwrite:
                logger.info(f"Resume {file_name} successfully overwritten profile ID {candidate.id}")
            else:
                logger.info(f"Resume {file_name} successfully parsed, saved, and indexed in Qdrant (candidate_id: {candidate.id})")
            return candidate

        except Exception as e:
            # Revert candidate transaction, mark raw resume as FAILED
            await db.rollback()
            db_resume.parse_status = "FAILED"
            db_resume.parse_error_message = str(e)
            await db.commit()

            logger.error(f"Failed to process and index resume: {e}")
            if isinstance(e, AIServiceError):
                raise
            raise AIServiceError(f"Failed to process and index resume: {e}") from e

    @classmethod
    async def parse_resume_session(cls, file_name: str, file_bytes: bytes, db: AsyncSession | None = None) -> dict:
        """
        Parses an uploaded resume PDF in-memory, completely bypassing database
        persistence and vector stores. If db is provided and the file hash already
        exists, retrieves the parsed details from database cache.
        """
        import re

        # Check if same resume is already present in DB by file hash
        file_hash = compute_file_hash(file_bytes)
        if file_hash and db:
            stmt = select(Resume).where(Resume.file_hash == file_hash)
            res = await db.execute(stmt)
            existing_resume = res.scalar_one_or_none()
            if existing_resume and existing_resume.parse_status == "SUCCESS":
                stmt_c = select(Candidate).options(selectinload(Candidate.skills)).where(Candidate.resume_id == existing_resume.id).order_by(Candidate.id.desc())
                c_res = await db.execute(stmt_c)
                candidate = c_res.scalars().first()
                if candidate:
                    logger.info(f"Session-wise Deduplication: Duplicate file hash detected (SHA-256: {file_hash}). Reusing existing candidate record and skipping LLM call.")

                    skills = [{"skill_name": s.skill_name} for s in candidate.skills]
                    projects = json.loads(candidate.projects_json) if candidate.projects_json else []
                    acc = json.loads(candidate.accomplishments_json) if candidate.accomplishments_json else []
                    hobbies = json.loads(candidate.hobbies_json) if candidate.hobbies_json else []
                    work_exp = json.loads(candidate.work_experience_json) if candidate.work_experience_json else []

                    return {
                        "candidate_name": candidate.candidate_name,
                        "email": candidate.email,
                        "phone_number": candidate.phone_number,
                        "primary_role_title": candidate.primary_role_title,
                        "primary_domain": candidate.primary_domain,
                        "total_experience_years": float(candidate.total_experience_years or 0.0),
                        "highest_education": candidate.highest_education,
                        "summary_text": candidate.summary_text,
                        "skills": skills,
                        "projects": projects,
                        "accomplishments": acc,
                        "hobbies": hobbies,
                        "work_experience": work_exp
                    }

        logger.info(f"Session-wise Processing: Parsing resume {file_name} in-memory")
        resume_text = extract_pdf_text(file_bytes)
        parsed_data = parse_resume_text(resume_text)

        # Regex validation to ensure parsed email contains @ and domain extension like .com, .co.in
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        parsed_email = parsed_data.get("email") or ""
        matches = re.findall(email_pattern, parsed_email)
        if not matches:
            # Fallback to search in raw resume_text
            text_matches = re.findall(email_pattern, resume_text)
            if text_matches:
                parsed_data["email"] = text_matches[0].strip()
            else:
                parsed_data["email"] = "candidate@example.com"
        else:
            parsed_data["email"] = matches[0].strip()

        # Write to database as a cache hit for future checks (even if candidate reloads/logouts)
        if db:
            try:
                db_resume = Resume(
                    file_name=file_name,
                    parse_status="SUCCESS",
                    file_hash=file_hash,
                    raw_text=resume_text
                )
                db.add(db_resume)
                await db.flush()

                exp_years = parsed_data.get("total_experience_years")
                total_exp = Decimal(str(exp_years)) if exp_years is not None else Decimal("0.0")
                skills_list = [s.get("skill_name", "") if isinstance(s, dict) else str(s) for s in parsed_data.get("skills", [])]
                skills_text = ", ".join(skills_list)

                # Check identity first to avoid duplicate Candidate records
                candidate = None
                email = parsed_data.get("email")
                phone = parsed_data.get("phone_number")
                name = parsed_data.get("candidate_name")
                if email:
                    stmt = select(Candidate).where(Candidate.email.ilike(email.strip())).order_by(Candidate.id.desc())
                    c_res = await db.execute(stmt)
                    candidate = c_res.scalars().first()
                if not candidate and name and phone:
                    stmt = select(Candidate).where(
                        Candidate.candidate_name.ilike(name.strip()),
                        Candidate.phone_number == phone.strip()
                    ).order_by(Candidate.id.desc())
                    c_res = await db.execute(stmt)
                    candidate = c_res.scalars().first()

                if candidate:
                    # Update resume link and field information
                    candidate.resume_id = db_resume.id
                    candidate.candidate_name = name or candidate.candidate_name
                    candidate.email = email or candidate.email
                    candidate.phone_number = phone or candidate.phone_number
                    candidate.primary_role_title = parsed_data.get("primary_role_title") or candidate.primary_role_title
                    candidate.primary_domain = parsed_data.get("primary_domain") or candidate.primary_domain
                    candidate.total_experience_years = total_exp
                    candidate.highest_education = parsed_data.get("highest_education") or candidate.highest_education
                    candidate.summary_text = parsed_data.get("summary_text") or candidate.summary_text
                    candidate.skills_text = skills_text
                    candidate.projects_json = json.dumps(parsed_data.get("projects", []))
                    candidate.accomplishments_json = json.dumps(parsed_data.get("accomplishments", []))
                    candidate.hobbies_json = json.dumps(parsed_data.get("hobbies", []))
                    candidate.work_experience_json = json.dumps(parsed_data.get("work_experience", []))
                else:
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
                        skills_text=skills_text,
                        projects_json=json.dumps(parsed_data.get("projects", [])),
                        accomplishments_json=json.dumps(parsed_data.get("accomplishments", [])),
                        hobbies_json=json.dumps(parsed_data.get("hobbies", [])),
                        work_experience_json=json.dumps(parsed_data.get("work_experience", []))
                    )
                    db.add(candidate)
                    await db.flush()

                # Sync skills
                from sqlalchemy import delete

                from app.models.candidate import CandidateSkill
                await db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == candidate.id))
                for s in parsed_data.get("skills", []):
                    skill_name = s.get("skill_name") if isinstance(s, dict) else str(s)
                    if skill_name:
                        db.add(CandidateSkill(candidate_id=candidate.id, skill_name=skill_name))

                await db.commit()
                logger.info(f"Session-wise Processing: Saved parsed resume {file_name} structure to DB cache for future uploads (SHA-256: {file_hash}).")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Session-wise Processing: Could not write parsed resume cache to database: {e}")

        return parsed_data

    @classmethod
    async def persist_parsed_candidate(cls, db: AsyncSession, data: dict, async_embed: bool = False) -> Candidate:
        """
        Saves a pre-parsed candidate profile directly to Postgres and indexes in Qdrant,
        using standard deduplication to update existing records if emails match.
        """
        email = data.get("email")
        phone = data.get("phone_number")
        name = data.get("name")

        # Check if they exist by email first
        candidate = None
        if email:
            stmt = select(Candidate).options(selectinload(Candidate.skills)).where(Candidate.email.ilike(email.strip())).order_by(Candidate.id.desc())
            res = await db.execute(stmt)
            candidate = res.scalars().first()

        if not candidate and name and phone:
            stmt = select(Candidate).options(selectinload(Candidate.skills)).where(
                Candidate.candidate_name.ilike(name.strip()),
                Candidate.phone_number == phone.strip()
            ).order_by(Candidate.id.desc())
            res = await db.execute(stmt)
            candidate = res.scalars().first()

        skills_list = data.get("skills", [])
        skills_text = ", ".join(skills_list)
        total_exp = Decimal(str(data.get("experience", 0.0)))

        # Create a placeholder Resume record
        db_resume = Resume(
            file_name="persisted_profile.pdf",
            parse_status="PENDING" if async_embed else "SUCCESS",
            raw_text=data.get("summary_text") or ""
        )
        db.add(db_resume)
        await db.flush()

        if candidate:
            # Overwrite existing candidate fields
            candidate.candidate_name = name or candidate.candidate_name
            candidate.email = email or candidate.email
            candidate.phone_number = phone or candidate.phone_number
            candidate.primary_role_title = data.get("role") or candidate.primary_role_title
            candidate.primary_domain = data.get("domain") or candidate.primary_domain
            candidate.total_experience_years = total_exp
            candidate.highest_education = data.get("highest_education") or candidate.highest_education
            candidate.summary_text = data.get("summary_text") or candidate.summary_text
            candidate.skills_text = skills_text
            candidate.projects_json = json.dumps(data.get("projects", []))
            candidate.accomplishments_json = json.dumps(data.get("accomplishments", []))
            candidate.hobbies_json = json.dumps(data.get("hobbies", []))
            candidate.work_experience_json = json.dumps(data.get("work_experience", []))

            # Clear old skills and write new ones
            stmt_del_skills = delete(CandidateSkill).where(CandidateSkill.candidate_id == candidate.id)
            await db.execute(stmt_del_skills)
            for skill in skills_list:
                db.add(CandidateSkill(candidate_id=candidate.id, skill_name=skill))

            # Replace candidate resume link
            old_resume_id = candidate.resume_id
            candidate.resume_id = db_resume.id
            if old_resume_id:
                stmt_del_res = delete(Resume).where(Resume.id == old_resume_id)
                await db.execute(stmt_del_res)
        else:
            # Create a brand new candidate
            candidate = Candidate(
                resume_id=db_resume.id,
                candidate_name=name,
                email=email,
                phone_number=phone,
                primary_role_title=data.get("role"),
                primary_domain=data.get("domain"),
                total_experience_years=total_exp,
                highest_education=data.get("highest_education"),
                summary_text=data.get("summary_text"),
                skills_text=skills_text,
                projects_json=json.dumps(data.get("projects", [])),
                accomplishments_json=json.dumps(data.get("accomplishments", [])),
                hobbies_json=json.dumps(data.get("hobbies", [])),
                work_experience_json=json.dumps(data.get("work_experience", []))
            )
            db.add(candidate)
            await db.flush()
            for skill in skills_list:
                db.add(CandidateSkill(candidate_id=candidate.id, skill_name=skill))

        await db.commit()
        await db.refresh(candidate)

        # Index/Overwrite in Qdrant
        if not async_embed:
            c_dict = {
                "primary_role_title": candidate.primary_role_title,
                "primary_domain": candidate.primary_domain,
                "total_experience_years": candidate.total_experience_years,
                "highest_education": candidate.highest_education,
                "summary_text": candidate.summary_text,
                "skills_text": candidate.skills_text,
            }
            profile_text = build_embedding_text(c_dict)
            model = cls.get_model()
            vector = model.encode(profile_text).tolist()

            payload = {
                "metadata": {
                    "candidate_id": candidate.id,
                    "candidate_name": candidate.candidate_name,
                    "primary_role_title": candidate.primary_role_title,
                    "primary_domain": candidate.primary_domain,
                    "total_experience_years": float(candidate.total_experience_years) if candidate.total_experience_years else 0.0,
                    "skills_text": candidate.skills_text,
                    "summary_text": candidate.summary_text,
                },
                "content": profile_text,
            }
            await VectorStore.upsert_chunks(
                ids=[candidate.id],
                vectors=[vector],
                payloads=[payload]
            )
            logger.info(f"Successfully persisted candidate ID {candidate.id} to Postgres and Qdrant.")
        else:
            logger.info(f"Successfully saved candidate ID {candidate.id} to PostgreSQL. Vector indexing will run asynchronously.")
        return candidate


