from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class MedicalExam(Base):
    __tablename__ = "medical_exams"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    
    # Exam details
    terminal_name = Column(String(64), nullable=True)
    result = Column(String(32), nullable=False)  # "passed", "failed"
    
    # Vitals
    pressure_systolic = Column(Integer, nullable=True)
    pressure_diastolic = Column(Integer, nullable=True)
    pulse = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    alcohol_mg_l = Column(Float, default=0.0, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    
    # Relationships
    employee = relationship("Employee", back_populates="exams")
