from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api import deps
from app.models.medical_exam import MedicalExam
from app.models.employee import Employee
from app.schemas.medical_exam import MedicalExamRead  # We need to create this schema

router = APIRouter()

@router.get("/exams")
def get_medical_exams(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    employee_id: Optional[int] = None,
    result: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Get list of medical exams.
    """
    query = db.query(MedicalExam)
    
    if employee_id:
        query = query.filter(MedicalExam.employee_id == employee_id)
    if result:
        query = query.filter(MedicalExam.result == result)
    if start_date:
        query = query.filter(MedicalExam.timestamp >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(MedicalExam.timestamp <= datetime.combine(end_date, datetime.max.time()))
        
    # Order by newest first
    query = query.order_by(MedicalExam.timestamp.desc())
    
    return query.offset(skip).limit(limit).all()

@router.get("/stats")
def get_medical_stats(
    db: Session = Depends(deps.get_db),
    target_date: date = Query(default_factory=date.today)
):
    """
    Get simple statistics for a specific date (default today).
    """
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())
    
    query = db.query(MedicalExam).filter(
        MedicalExam.timestamp >= start,
        MedicalExam.timestamp <= end
    )
    
    total = query.count()
    passed = query.filter(MedicalExam.result == 'passed').count()
    failed = query.filter(MedicalExam.result == 'failed').count()
    
    return {
        "date": target_date,
        "total": total,
        "passed": passed,
        "failed": failed
    }
