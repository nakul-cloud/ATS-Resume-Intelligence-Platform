import json
from decimal import Decimal
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate, CandidateSkill, Resume
from app.utils.logger import logger
from app.constants.jobs import STATUS_SUCCESS, STATUS_PENDING
from app.services.ai.embedder import EmbeddingService
from app.services.ai.vector_store import VectorStore

class CandidatePersistService:
    @classmethod
    async def persist_parsed_candidate(
        cls, db: AsyncSession, data: dict, async_embed: bool = False
    ) -> Candidate:
        """
        Saves a pre-parsed candidate profile directly to Postgres and indexes in Qdrant,
        using standard deduplication to update existing records if emails match.
        """
        email = data.get("email")
        phone = data.get("phone_number")
        name = data.get("name")

        candidate = await cls._lookup_candidate(db, email, name, phone)

        skills_list = data.get("skills", [])
        skills_text = ", ".join(skills_list)
        total_exp = Decimal(str(data.get("experience", 0.0)))

        # Create a placeholder Resume record
        db_resume = Resume(
            file_name="persisted_profile.pdf",
            parse_status=STATUS_PENDING if async_embed else STATUS_SUCCESS,
            raw_text=data.get("summary_text") or "",
        )
        db.add(db_resume)
        await db.flush()

        if candidate:
            await cls._overwrite_candidate_details(
                db, candidate, data, total_exp, skills_list, skills_text, db_resume
            )
        else:
            candidate = await cls._create_new_candidate_record(
                db, data, total_exp, skills_list, skills_text, db_resume
            )

        await db.commit()
        await db.refresh(candidate)

        # Index/Overwrite in Qdrant
        if not async_embed:
            await cls._index_in_qdrant(candidate)
            logger.info(
                f"Successfully persisted candidate ID {candidate.id} to Postgres and Qdrant."
            )
        else:
            logger.info(
                f"Successfully saved candidate ID {candidate.id} to PostgreSQL. Vector indexing will run asynchronously."
            )
        return candidate

    @classmethod
    async def _lookup_candidate(
        cls, db: AsyncSession, email: str | None, name: str | None, phone: str | None
    ) -> Candidate | None:
        """Looks up candidate by email or candidate_name/phone_number."""
        if email:
            stmt = (
                select(Candidate)
                .options(selectinload(Candidate.skills))
                .where(Candidate.email.ilike(email.strip()))
                .order_by(Candidate.id.desc())
            )
            res = await db.execute(stmt)
            candidate = res.scalars().first()
            if candidate:
                return candidate

        if name and phone:
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
            return res.scalars().first()

        return None

    @classmethod
    async def _overwrite_candidate_details(
        cls,
        db: AsyncSession,
        candidate: Candidate,
        data: dict,
        total_exp: Decimal,
        skills_list: list[str],
        skills_text: str,
        db_resume: Resume,
    ) -> None:
        """Overwrites existing candidate details, replaces skills, and handles old resume deletions."""
        candidate.candidate_name = data.get("name") or candidate.candidate_name
        candidate.email = data.get("email") or candidate.email
        candidate.phone_number = data.get("phone_number") or candidate.phone_number
        candidate.primary_role_title = data.get("role") or candidate.primary_role_title
        candidate.primary_domain = data.get("domain") or candidate.primary_domain
        candidate.total_experience_years = total_exp
        candidate.highest_education = (
            data.get("highest_education") or candidate.highest_education
        )
        candidate.summary_text = data.get("summary_text") or candidate.summary_text
        candidate.skills_text = skills_text
        candidate.projects_json = json.dumps(data.get("projects", []))
        candidate.accomplishments_json = json.dumps(data.get("accomplishments", []))
        candidate.hobbies_json = json.dumps(data.get("hobbies", []))
        candidate.work_experience_json = json.dumps(data.get("work_experience", []))

        # Clear old skills and write new ones
        stmt_del_skills = delete(CandidateSkill).where(
            CandidateSkill.candidate_id == candidate.id
        )
        await db.execute(stmt_del_skills)
        for skill in skills_list:
            db.add(CandidateSkill(candidate_id=candidate.id, skill_name=skill))

        # Replace candidate resume link
        old_resume_id = candidate.resume_id
        candidate.resume = db_resume
        await db.flush()
        await cls._cleanup_old_resume(db, old_resume_id, db_resume.id)

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
    async def _create_new_candidate_record(
        cls,
        db: AsyncSession,
        data: dict,
        total_exp: Decimal,
        skills_list: list[str],
        skills_text: str,
        db_resume: Resume,
    ) -> Candidate:
        """Creates a brand new candidate record and adds their skill relationships."""
        candidate = Candidate(
            resume_id=db_resume.id,
            candidate_name=data.get("name"),
            email=data.get("email"),
            phone_number=data.get("phone_number"),
            primary_role_title=data.get("role"),
            primary_domain=data.get("domain"),
            total_experience_years=total_exp,
            highest_education=data.get("highest_education"),
            summary_text=data.get("summary_text"),
            skills_text=skills_text,
            projects_json=json.dumps(data.get("projects", [])),
            accomplishments_json=json.dumps(data.get("accomplishments", [])),
            hobbies_json=json.dumps(data.get("hobbies", [])),
            work_experience_json=json.dumps(data.get("work_experience", [])),
        )
        db.add(candidate)
        await db.flush()
        for skill in skills_list:
            db.add(CandidateSkill(candidate_id=candidate.id, skill_name=skill))
        return candidate

    @classmethod
    async def _index_in_qdrant(cls, candidate: Candidate) -> None:
        """Generates and upserts profile embeddings into Qdrant for search matching."""
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
