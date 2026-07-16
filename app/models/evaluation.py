from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .candidate import Candidate
    from .interview import InterviewSession
    from .project import RecommendedProject



class DecisionBand(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Evaluation(Base, TimestampMixin):
    """One JD-vs-candidate scoring run -- output of the Evaluation + Decision agents."""

    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates_parsed.id", ondelete="CASCADE"))

    job_description_text: Mapped[str] = mapped_column(Text, nullable=False)
    match_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    decision_band: Mapped[DecisionBand] = mapped_column(
        Enum(DecisionBand, name="decisionband", native_enum=True), nullable=False
    )

    candidate: Mapped[Candidate] = relationship(back_populates="evaluations")
    strengths: Mapped[list[EvaluationStrength]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )
    skill_gaps: Mapped[list[EvaluationSkillGap]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )
    comparisons: Mapped[list[EvaluationComparison]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan", order_by="EvaluationComparison.rank"
    )
    recommended_projects: Mapped[list[RecommendedProject]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[list[InterviewSession]] = relationship(back_populates="evaluation")


class EvaluationStrength(Base):
    """One strength called out for a candidate in a given evaluation run."""

    __tablename__ = "evaluation_strengths"

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"))
    strength_text: Mapped[str] = mapped_column(String(500), nullable=False)

    evaluation: Mapped[Evaluation] = relationship(back_populates="strengths")


class EvaluationSkillGap(Base):
    """One skill gap called out for a candidate in a given evaluation run."""

    __tablename__ = "evaluation_skill_gaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"))
    gap_text: Mapped[str] = mapped_column(String(500), nullable=False)

    evaluation: Mapped[Evaluation] = relationship(back_populates="skill_gaps")


class EvaluationComparison(Base, TimestampMixin):
    """
    Join table recording where a candidate ranked against the other stored resumes
    for this evaluation's JD -- i.e. the self-eval vector similarity results from Qdrant,
    persisted for audit/history rather than kept only in the vector store.
    """

    __tablename__ = "evaluation_comparisons"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "compared_candidate_id", name="uq_evaluation_compared_candidate"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"))
    compared_candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates_parsed.id", ondelete="CASCADE")
    )

    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)  # cosine similarity from Qdrant
    rank: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = most similar to the JD

    evaluation: Mapped[Evaluation] = relationship(back_populates="comparisons")
    compared_candidate: Mapped[Candidate] = relationship(back_populates="appeared_in_comparisons")
