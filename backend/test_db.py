import logging
import sys
from app.db.session import SessionLocal
from app.models.medical_exam import MedicalExam
from app.models.employee import Employee
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_db")

def test_db():
    db = SessionLocal()
    try:
        # Check counts
        exam_count = db.query(MedicalExam).count()
        emp_count = db.query(Employee).count()
        print(f"DEBUG_INFO: EXAMS={exam_count}, EMPLOYEES={emp_count}")
        
        # Try a tiny write
        # Find first employee if any exists
        emp = db.query(Employee).first()
        if emp:
            print(f"DEBUG_INFO: EMP_ID={emp.id}, EMP_NAME={emp.first_name}")
        else:
            print("DEBUG_INFO: NO_EMPLOYEES")
            
    except Exception as e:
        print(f"DEBUG_ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_db()
