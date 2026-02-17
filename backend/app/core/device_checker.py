import asyncio
import logging
import socket
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.device import Device, DeviceType

logger = logging.getLogger("minetrack.checker")

async def check_device_online(host: str, port: int = 80, timeout: int = 2) -> bool:
    """Check if a device is reachable via TCP."""
    if not host:
        return False
    try:
        # Using a low-level socket for a quick TCP connect test
        loop = asyncio.get_event_loop()
        conn = loop.run_in_executor(None, lambda: socket.create_connection((host, port), timeout=timeout))
        sock = await conn
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

async def device_status_worker():
    """Background task to update device last_seen/is_active based on reachability."""
    logger.info("Device status worker started")
    while True:
        db = SessionLocal()
        try:
            devices = db.query(Device).all()
            for device in devices:
                # We mainly check HIKVISION devices for now
                if device.device_type == DeviceType.HIKVISION and device.host:
                    is_online = await check_device_online(device.host)
                    if is_online:
                        device.last_seen = datetime.now(timezone.utc)
                        # Optional: device.is_active = True
                        db.commit()
                        logger.debug("Device %s (%s) is ONLINE", device.name, device.host)
                    else:
                        logger.debug("Device %s (%s) is OFFLINE", device.name, device.host)
        except Exception as e:
            logger.error("Error in device status worker: %s", e)
        finally:
            db.close()
            
        # Check every 1 minute
        await asyncio.sleep(60)
