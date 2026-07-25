from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone

from app.core.database import Base


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id"),
        nullable=False
    )
    snapshot_minio_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False
    )
    detected_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    attendance_logs: Mapped[list["AttendanceLog"]] = relationship(
        "AttendanceLog", 
        back_populates="session", 
        cascade="all, delete-orphan"
    )
    unit: Mapped["Unit"] = relationship(
        "Unit",
        back_populates="sessions"
    )