from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, String, Float, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.prisoners.models import Prisoner


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    prisoner_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("prisoners.id", ondelete="SET NULL"),
        nullable=True
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now()
    )
    snapshot_url: Mapped[str] = mapped_column(String(512), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    attend: Mapped[bool] = mapped_column(Boolean, nullable=False)

    prisoner: Mapped[Optional["Prisoner"]] = relationship(back_populates="attendance_log")