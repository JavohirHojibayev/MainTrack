from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MedicalExamEmployee(BaseModel):
    id: int
    employee_no: str
    first_name: str
    last_name: str
    patronymic: Optional[str] = None

    class Config:
        from_attributes = True


class MedicalExamBase(BaseModel):
    result: str
    terminal_name: Optional[str] = None
    pressure_systolic: Optional[int] = None
    pressure_diastolic: Optional[int] = None
    pulse: Optional[int] = None
    temperature: Optional[float] = None
    alcohol_mg_l: Optional[float] = None
    timestamp: datetime

class MedicalExamRead(MedicalExamBase):
    id: int
    employee_id: int
    employee_full_name: Optional[str] = None
    employee: Optional[MedicalExamEmployee] = None
    
    class Config:
        from_attributes = True
