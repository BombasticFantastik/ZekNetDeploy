from sqlalchemy import String, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from typing import List

from datetime import datetime
from app.core.database import Base


class PrisonerEtalon(Base):
    __tablename__ = "prisoners_etalons"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Добавил ФИО человека
    fio: Mapped[str] = mapped_column(String(255), nullable=True)
    photo_minio_path: Mapped[str] = mapped_column(
        String(512), 
        nullable=False,
        unique=True
    )
    face_embedding: Mapped[Vector] = mapped_column(Vector(512), nullable=False)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=func.now()
    )
    

    attendance_logs: Mapped[List["AttendanceLog"]] = relationship(
        "AttendanceLog",
        back_populates="matched_prisoner"
    )
    schedules: Mapped[List["PrisonerSchedule"]] = relationship(
        "PrisonerSchedule",
        back_populates="prisoner",
        cascade="all, delete-orphan"
    )
    unit: Mapped["Unit"] = relationship(
        "Unit",
        back_populates="prisoners"
    )


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)

    prisoners: Mapped[List["PrisonerEtalon"]] = relationship(
        "PrisonerEtalon",
        back_populates="unit"
    )    
    sessions: Mapped[list["AttendanceSession"]] = relationship(
        "AttendanceSession",
        back_populates="unit"
    )                     