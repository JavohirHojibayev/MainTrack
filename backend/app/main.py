import logging
# Force reload 2
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings

from app.core.device_checker import device_status_worker

logger = logging.getLogger("minetrack")

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Hikvision webhook mode active — turnstiles push events to /api/v1/hikvision/webhook")
    
    # Start device status background checker
    checker_task = asyncio.create_task(device_status_worker())
    
    yield
    
    # Clean up
    checker_task.cancel()
    try:
        await checker_task
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
