from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .evaluation import Evaluation, EvaluationComparison
    from .interview import InterviewSession
    from .rewrite import RewriteSuggestion



class Resume(Base, TimestampMixin):
    """One uploaded resume file, pre-parsing."""

    __tablename__ = "resumes_raw"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500))
    parse_status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING / SUCCESS / FAILED
    parse_error_message: Mapped[str | None] = mapped_column(Text)
    file_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    raw_text: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped[Candidate | None] = relationship(
        back_populates="resume", uselist=False, cascade="all, delete-orphan"
    )


class Candidate(Base, TimestampMixin):
    """LLM-parsed structured output of a resume. No embedding column -- lives in Qdrant, keyed by this id."""

    __tablename__ = "candidates_parsed"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes_raw.id", ondelete="CASCADE"))

    candidate_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(String(30))
    primary_role_title: Mapped[str | None] = mapped_column(String(255))
    primary_domain: Mapped[str | None] = mapped_column(String(255))
    total_experience_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    highest_education: Mapped[str | None] = mapped_column(String(255))
    summary_text: Mapped[str | None] = mapped_column(Text)
    skills_text: Mapped[str | None] = mapped_column(Text)
    projects_json: Mapped[str | None] = mapped_column(Text)
    accomplishments_json: Mapped[str | None] = mapped_column(Text)
    hobbies_json: Mapped[str | None] = mapped_column(Text)
    work_experience_json: Mapped[str | None] = mapped_column(Text)

    resume: Mapped[Resume] = relationship(back_populates="candidate")
    skills: Mapped[list[CandidateSkill]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list[Evaluation]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[list[InterviewSession]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    rewrite_suggestions: Mapped[list[RewriteSuggestion]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    # Rows where this candidate showed up as one of the ranked comparisons in someone else's evaluation
    appeared_in_comparisons: Mapped[list[EvaluationComparison]] = relationship(
        back_populates="compared_candidate", cascade="all, delete-orphan"
    )


class CandidateSkill(Base):
    """Normalized skill_text -> individual rows, used for filtering/faceting without hitting Qdrant."""

    __tablename__ = "candidate_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates_parsed.id", ondelete="CASCADE"))
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)

    candidate: Mapped[Candidate] = relationship(back_populates="skills")
