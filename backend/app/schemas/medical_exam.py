from datetime import datetime
from typing import Optional
from pydantic import BaseModel

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
    
    class Config:
        from_attributes = True
