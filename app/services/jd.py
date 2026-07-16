import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.jd_rewrite_agent import parse_and_normalize_jd
from app.exceptions.custom_exceptions import AIServiceError
from app.models.jd_cache import JDCache
from app.utils.logger import logger


class JDService:

    @classmethod
    async def normalize_job_description(cls, db: AsyncSession, jd_text: str) -> dict:
        """
        Invokes the JD Rewrite Agent to structure and normalize a raw Job Description,
        utilizing a PostgreSQL cache table to bypass the LLM for duplicate requests.
        """
        if not jd_text or not jd_text.strip():
            return {}

        # 1. Compute hash of the clean JD text
        clean_text = jd_text.strip()
        jd_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()

        # 2. Check PostgreSQL cache first
        try:
            stmt = select(JDCache).where(JDCache.jd_hash == jd_hash)
            res = await db.execute(stmt)
            cache_rec = res.scalar_one_or_none()

            if cache_rec:
                logger.info("JD Normalization: Cache HIT! Bypassing Groq LLM API call.")
                return json.loads(cache_rec.normalized_json)
        except Exception as cache_err:
            logger.warning(f"Failed to read from PostgreSQL JD cache table: {cache_err}")

        # 3. Cache Miss: Run parser LLM agent
        logger.info("JD Normalization: Cache MISS. Calling Groq LLM API to normalize Job Description.")
        try:
            structured_jd = parse_and_normalize_jd(clean_text)

            # 4. Save to PostgreSQL cache
            try:
                cache_rec = JDCache(jd_hash=jd_hash, normalized_json=json.dumps(structured_jd))
                db.add(cache_rec)
                await db.commit()
                logger.info("Successfully saved normalized JD to PostgreSQL cache table.")
            except Exception as cache_save_err:
                logger.warning(f"Failed to save normalized JD to PostgreSQL cache table: {cache_save_err}")

            return structured_jd
        except Exception as e:
            logger.error(f"JD Service normalization failed: {e}")
            if isinstance(e, AIServiceError):
                raise
            raise AIServiceError(f"JD normalization failed: {e}") from e
