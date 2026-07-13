from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class ResumeRewriteCache(Base, TimestampMixin):
    """
    Cache table to store similarity-based optimization results.
    """
    __tablename__ = "rewrite_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    jd_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    focus_areas_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    optimized_result_json: Mapped[str] = mapped_column(Text, nullable=False)
    raw_jd_text: Mapped[str | None] = mapped_column(Text)
    raw_candidate_text: Mapped[str | None] = mapped_column(Text)
