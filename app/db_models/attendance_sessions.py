from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from datetime import datetime

from app.core.database import Base


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_minio_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False
    )
    detected_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now()
    )

    attendance_logs: Mapped[list["AttendanceLog"]] = relationship(
        "AttendanceLog", 
        back_populates="session", 
        cascade="all, delete-orphan"
    )