from sqlalchemy import String, Integer, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from app.core.database import Base


class PrisonerSchedule(Base):
    """
    График/расписание статусов заключенного.
    Позволяет отмечать, где должен находиться заключенный в конкретный день.
    
    Возможные статусы:
    - PRESENT: Присутствует в отряде
    - BUSINESS_TRIP: Командировка
    - HOSPITAL: В больнице
    - VACATION: В отпуске
    - DISCIPLINARY: Дисциплинарное отделение
    - OTHER: Другое
    """
    __tablename__ = "prisoner_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    prisoner_id: Mapped[int] = mapped_column(
        ForeignKey("prisoners_etalons.id", ondelete="CASCADE"),
        nullable=False
    )
    date: Mapped["Date"] = mapped_column(Date, nullable=False)  # Дата без времени
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="PRESENT"
    )
    note: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )  # Примечание (например, "Приказ №12")

    # Связь с заключенным
    prisoner: Mapped["PrisonerEtalon"] = relationship(
        "PrisonerEtalon",
        back_populates="schedules"
    )
