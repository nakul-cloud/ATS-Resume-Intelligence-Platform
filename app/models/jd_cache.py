from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class JDCache(Base, TimestampMixin):
    __tablename__ = "jd_cache"

    jd_hash: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    normalized_json: Mapped[str] = mapped_column(Text, nullable=False)
