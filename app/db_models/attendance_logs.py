from sqlalchemy import String, Integer, DateTime, func, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from datetime import datetime
from app.core.database import Base


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    matched_prisoner_id: Mapped[int] = mapped_column(
        ForeignKey("prisoners_etalons.id", ondelete="SET NULL"),
        nullable=True
    )
    session_id: Mapped[int] = mapped_column(
        ForeignKey(
            "attendance_sessions.id",
            ondelete="CASCADE"
        ), 
        nullable=False
    )
    face_detection_score: Mapped[float] = mapped_column(
        nullable=False
    )
    match_distance: Mapped[float | None] = mapped_column(
        nullable=True
    )
    is_verified: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )
    bbox: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    cropped_face_minio_path: Mapped[str] = mapped_column(String(512), nullable=False)

    session: Mapped["AttendanceSession"] = relationship(
        "AttendanceSession", 
        back_populates="attendance_logs"
    )
    matched_prisoner: Mapped[Optional["PrisonerEtalon"]] = relationship(
        "PrisonerEtalon", 
        back_populates="attendance_logs"
    )