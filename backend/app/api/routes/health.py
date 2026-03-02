from fastapi import APIRouter

from app.core.config import settings
from app.core.esmo_monitoring import (
    get_esmo_health_state,
    get_poller_metrics,
    run_esmo_health_check,
)

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/esmo")
def health_esmo(run_now: bool = False, n: int | None = None) -> dict:
    health_state = run_esmo_health_check(n=n) if run_now else get_esmo_health_state()
    return {
        "enabled": settings.ESMO_ENABLED,
        "poller": get_poller_metrics(),
        "consistency": health_state,
    }
