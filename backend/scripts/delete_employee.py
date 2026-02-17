import sys
import os

# Add parent directory to path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.employee import Employee
from app.models.event import Event

def delete_employee(emp_no):
    db = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.employee_no == emp_no).first()
        if emp:
            print(f"Found employee: {emp.last_name} {emp.first_name} {emp.patronymic} (ID: {emp.id}, No: {emp.employee_no})")
            
            # Delete events
            event_count = db.query(Event).filter(Event.employee_id == emp.id).count()
            if event_count > 0:
                print(f"Deleting {event_count} associated events...")
                db.query(Event).filter(Event.employee_id == emp.id).delete()
            
            db.delete(emp)
            db.commit()
            print("Employee and associated events deleted successfully.")
        else:
            print(f"Employee with number '{emp_no}' not found.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        delete_employee(sys.argv[1])
    else:
        print("Usage: python delete_employee.py <employee_no>")
