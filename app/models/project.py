from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .evaluation import Evaluation



class RecommendedProject(Base, TimestampMixin):
    """Project suggestions from the personalized roadmap output, targeting a specific skill gap."""

    __tablename__ = "recommended_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"))

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target_skill: Mapped[str | None] = mapped_column(String(255))
    priority: Mapped[str] = mapped_column(String(10), default="MEDIUM")  # LOW / MEDIUM / HIGH

    evaluation: Mapped["Evaluation"] = relationship(back_populates="recommended_projects")