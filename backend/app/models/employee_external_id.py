from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class EmployeeExternalID(Base):
    __tablename__ = "employee_external_ids"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("minetrack.employees.id"), nullable=False, index=True)
    system = Column(String(32), nullable=False)
    external_id = Column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("system", "external_id", name="uq_employee_external_ids_system_external_id"),
        UniqueConstraint("employee_id", "system", name="uq_employee_external_ids_employee_system"),
    )

    employee = relationship("Employee", back_populates="external_ids")
