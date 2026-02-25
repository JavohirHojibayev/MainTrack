import logging
# Force reload 2
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.device_checker import device_status_worker
from app.core.esmo_poller import esmo_polling_loop
from app.core.hikvision_poller import hikvision_polling_loop

logger = logging.getLogger("minetrack")

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Hikvision webhook mode active — turnstiles push events to /api/v1/hikvision/webhook")
    
    # Start background tasks
    checker_task = asyncio.create_task(device_status_worker())
    hikvision_task = asyncio.create_task(hikvision_polling_loop())
    esmo_task = None
    if settings.ESMO_ENABLED:
        esmo_task = asyncio.create_task(esmo_polling_loop())
    else:
        logger.warning("ESMO polling is disabled (ESMO_ENABLED=false)")
    
    yield
    
    # Clean up
    checker_task.cancel()
    hikvision_task.cancel()
    if esmo_task:
        esmo_task.cancel()
    try:
        tasks = [checker_task, hikvision_task]
        if esmo_task:
            tasks.append(esmo_task)
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        pass


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root() -> dict:
    return {"name": settings.PROJECT_NAME, "status": "running"}
