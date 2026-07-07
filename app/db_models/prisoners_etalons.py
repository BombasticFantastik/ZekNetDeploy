from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from typing import List

from datetime import datetime
from app.core.database import Base


class PrisonerEtalon(Base):
    __tablename__ = "prisoners_etalons"

    id: Mapped[int] = mapped_column(primary_key=True)
    photo_minio_path: Mapped[str] = mapped_column(
        String(512), 
        nullable=False,
        unique=True
    )
    face_embedding: Mapped[Vector] = mapped_column(Vector(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=func.now()
    )

    attendance_logs: Mapped[List["AttendanceLog"]] = relationship(
        "AttendanceLog",
        back_populates="matched_prisoner"
    )