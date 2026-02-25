from fastapi import APIRouter

from app.api.routes import auth, devices, employees, events, health, hikvision, medical, reports, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(hikvision.router, prefix="/hikvision", tags=["hikvision"])
api_router.include_router(medical.router, prefix="/medical", tags=["medical"])

