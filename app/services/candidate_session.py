import json
from decimal import Decimal
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate, CandidateSkill, Resume
from app.utils.deduplication import compute_file_hash
from app.utils.pdf_extractor import extract_pdf_text
from app.utils.json_utils import parse_json_list
from app.utils.logger import logger
from app.agents.resume_parser_agent import parse_resume_text
from app.constants.jobs import STATUS_SUCCESS

class CandidateSessionService:
    @classmethod
    async def parse_resume_session(
        cls, file_name: str, file_bytes: bytes, db: AsyncSession | None = None
    ) -> dict:
        """
        Parses an uploaded resume PDF in-memory, completely bypassing database
        persistence and vector stores. If db is provided and the file hash already
        exists, retrieves the parsed details from database cache.
        """
        file_hash = compute_file_hash(file_bytes)
        if db:
            cached_data = await cls._lookup_session_cache(db, file_hash)
            if cached_data:
                return cached_data

        logger.info(f"Session-wise Processing: Parsing resume {file_name} in-memory")
        resume_text = extract_pdf_text(file_bytes)
        parsed_data = parse_resume_text(resume_text)

        # Ensure valid email structure via regex pattern checking
        parsed_data["email"] = cls._extract_session_email(
            parsed_data.get("email"), resume_text
        )

        # Write to database as a cache hit for future checks (even if candidate reloads/logouts)
        if db:
            await cls._cache_session_result(
                db, file_name, file_hash, resume_text, parsed_data
            )

        return parsed_data

    @classmethod
    async def _lookup_session_cache(
        cls, db: AsyncSession, file_hash: str | None
    ) -> dict | None:
        """Looks up the database for cached parsed resume session data using the file hash."""
        if not file_hash:
            return None
        stmt = select(Resume).where(Resume.file_hash == file_hash)
        res = await db.execute(stmt)
        existing_resume = res.scalar_one_or_none()
        if existing_resume and existing_resume.parse_status == STATUS_SUCCESS:
            stmt_c = (
                select(Candidate)
                .options(selectinload(Candidate.skills))
                .where(Candidate.resume_id == existing_resume.id)
                .order_by(Candidate.id.desc())
            )
            c_res = await db.execute(stmt_c)
            candidate = c_res.scalars().first()
            if candidate:
                logger.info(
                    f"Session-wise Deduplication: Duplicate file hash detected (SHA-256: {file_hash}). Reusing existing candidate record and skipping LLM call."
                )

                skills = [{"skill_name": s.skill_name} for s in candidate.skills]
                projects = parse_json_list(candidate.projects_json)
                acc = parse_json_list(candidate.accomplishments_json)
                hobbies = parse_json_list(candidate.hobbies_json)
                work_exp = parse_json_list(candidate.work_experience_json)

                return {
                    "candidate_name": candidate.candidate_name,
                    "email": candidate.email,
                    "phone_number": candidate.phone_number,
                    "primary_role_title": candidate.primary_role_title,
                    "primary_domain": candidate.primary_domain,
                    "total_experience_years": float(
                        candidate.total_experience_years or 0.0
                    ),
                    "highest_education": candidate.highest_education,
                    "summary_text": candidate.summary_text,
                    "skills": skills,
                    "projects": projects,
                    "accomplishments": acc,
                    "hobbies": hobbies,
                    "work_experience": work_exp,
                }
        return None

    @staticmethod
    def _is_valid_email(addr: str) -> bool:
        """Returns True if addr has the structural shape of a valid email address."""
        addr = addr.strip()
        if not addr or " " in addr or "@" not in addr:
            return False
        local, _, domain = addr.partition("@")
        if not local or not domain or domain.startswith(".") or domain.endswith("."):
            return False
        return "." in domain

    @staticmethod
    def _scan_email_tokens(text: str) -> str | None:
        """Scans whitespace-delimited tokens and returns the first valid email found."""
        strip_chars = ".,;:<>\"'()[]{}"
        for token in text.split():
            candidate = token.strip(strip_chars)
            if CandidateSessionService._is_valid_email(candidate):
                return candidate
        return None

    @classmethod
    def _extract_session_email(cls, parsed_email: str | None, resume_text: str) -> str:
        """
        Extracts a well-formed email address from parsed LLM output or raw resume text.
        Uses pure string operations to avoid any regex backtracking risk (S5852).
        """
        # 1. Use the parsed email directly if it is already valid
        if parsed_email and cls._is_valid_email(parsed_email.strip()):
            return parsed_email.strip()

        # 2. Scan tokens in the parsed email string (e.g. "Email: foo@bar.com")
        found = cls._scan_email_tokens(parsed_email or "")
        if found:
            return found

        # 3. Scan the full resume text as a last resort
        found = cls._scan_email_tokens(resume_text)
        if found:
            return found

        return "candidate@example.com"

    @classmethod
    async def _cache_session_result(
        cls,
        db: AsyncSession,
        file_name: str,
        file_hash: str | None,
        resume_text: str,
        parsed_data: dict,
    ) -> None:
        """Saves parsed resume session data as a cache hit in the database."""
        try:
            # Check if a resume with this hash already exists to avoid UniqueViolationError
            existing_resume = None
            if file_hash:
                stmt_res = select(Resume).where(Resume.file_hash == file_hash)
                res_res = await db.execute(stmt_res)
                existing_resume = res_res.scalar_one_or_none()

            if existing_resume:
                db_resume = existing_resume
                db_resume.file_name = file_name
                db_resume.parse_status = STATUS_SUCCESS
                db_resume.raw_text = resume_text
            else:
                db_resume = Resume(
                    file_name=file_name,
                    parse_status=STATUS_SUCCESS,
                    file_hash=file_hash,
                    raw_text=resume_text,
                )
                db.add(db_resume)
            await db.flush()

            exp_years = parsed_data.get("total_experience_years")
            total_exp = (
                Decimal(str(exp_years)) if exp_years is not None else Decimal("0.0")
            )
            skills_list = [
                s.get("skill_name", "") if isinstance(s, dict) else str(s)
                for s in parsed_data.get("skills", [])
            ]
            skills_text = ", ".join(skills_list)

            # Check identity first to avoid duplicate Candidate records
            email = parsed_data.get("email")
            phone = parsed_data.get("phone_number")
            name = parsed_data.get("candidate_name")
            candidate = await cls._lookup_candidate(db, email, name, phone)

            if candidate:
                candidate.resume_id = db_resume.id
                candidate.candidate_name = name or candidate.candidate_name
                candidate.email = email or candidate.email
                candidate.phone_number = phone or candidate.phone_number
                candidate.primary_role_title = (
                    parsed_data.get("primary_role_title")
                    or candidate.primary_role_title
                )
                candidate.primary_domain = (
                    parsed_data.get("primary_domain") or candidate.primary_domain
                )
                candidate.total_experience_years = total_exp
                candidate.highest_education = (
                    parsed_data.get("highest_education") or candidate.highest_education
                )
                candidate.summary_text = (
                    parsed_data.get("summary_text") or candidate.summary_text
                )
                candidate.skills_text = skills_text
                candidate.projects_json = json.dumps(parsed_data.get("projects", []))
                candidate.accomplishments_json = json.dumps(
                    parsed_data.get("accomplishments", [])
                )
                candidate.hobbies_json = json.dumps(parsed_data.get("hobbies", []))
                candidate.work_experience_json = json.dumps(
                    parsed_data.get("work_experience", [])
                )
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
                    accomplishments_json=json.dumps(
                        parsed_data.get("accomplishments", [])
                    ),
                    hobbies_json=json.dumps(parsed_data.get("hobbies", [])),
                    work_experience_json=json.dumps(
                        parsed_data.get("work_experience", [])
                    ),
                )
                db.add(candidate)
                await db.flush()

            # Sync skills
            await cls._sync_candidate_skills(
                db, candidate.id, parsed_data.get("skills", [])
            )

            await db.commit()
            logger.info(
                f"Session-wise Processing: Saved parsed resume {file_name} structure to DB cache for future uploads (SHA-256: {file_hash})."
            )
        except Exception as cache_err:
            await db.rollback()
            logger.warning(
                f"Session-wise Processing: Could not write parsed resume cache to database: {cache_err}"
            )

    @classmethod
    async def _sync_candidate_skills(
        cls, db: AsyncSession, candidate_id: int, skills_data: list
    ) -> None:
        """Helper to sync candidate skill relations."""
        await db.execute(
            delete(CandidateSkill).where(CandidateSkill.candidate_id == candidate_id)
        )
        for s in skills_data:
            skill_name = s.get("skill_name") if isinstance(s, dict) else str(s)
            if skill_name:
                db.add(CandidateSkill(candidate_id=candidate_id, skill_name=skill_name))

    @classmethod
    async def _lookup_candidate(
        cls, db: AsyncSession, email: str | None, name: str | None, phone: str | None
    ) -> Candidate | None:
        """Looks up a candidate by email or matching name and phone to prevent duplication."""
        if email:
            stmt = select(Candidate).where(Candidate.email.ilike(email.strip()))
            res = await db.execute(stmt)
            cand = res.scalars().first()
            if cand:
                return cand

        if name and phone:
            stmt = select(Candidate).where(
                Candidate.candidate_name.ilike(name.strip()),
                Candidate.phone_number == phone.strip(),
            )
            res = await db.execute(stmt)
            cand = res.scalars().first()
            if cand:
                return cand

        return None
