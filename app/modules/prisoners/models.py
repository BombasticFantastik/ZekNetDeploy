from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Float, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base
from app.modules.attendance.models import AttendanceLog

class Prisoner(Base):
    __tablename__ = "prisoners"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=True)
    second_name: Mapped[str] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str] = mapped_column(String(255), nullable=True)
    
    photo_url: Mapped[str] = mapped_column(String(512), nullable=False)
    face_embedding: Mapped[Vector] = mapped_column(Vector(512), nullable=False)

    attendance_log: Mapped[List["AttendanceLog"]] = relationship(
        back_populates="prisoner"
    )