import asyncio
import json
import logging
import ssl
import websockets
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.medical_exam import MedicalExam
from app.models.employee import Employee

# Configure logging
logger = logging.getLogger(__name__)

ESMO_WS_URL = "wss://192.168.8.10/ws_connect?group_id=8"

# Whitelist of allowed terminals
ALLOWED_TERMINALS = {
    "192.168.8.17": {"serial": "SN020245001", "name": "TKM 1-terminal", "model": "MT-02", "api_key": "351bb06ecee5549db1a79fb8703283dd"},
    "192.168.8.18": {"serial": "SN020245009", "name": "TKM 2-terminal", "model": "MT-02", "api_key": "50624db1b29f6486d7121d2597640879"},
    "192.168.8.19": {"serial": "SN020245002", "name": "TKM 3-terminal", "model": "MT",    "api_key": "0862df127d6f3fd7585586e58722750c"},
    "192.168.8.20": {"serial": "SN020245004", "name": "TKM 4-terminal", "model": "MT-02", "api_key": "91345b4dd27a3bbaec1a5b1476e978bc"},
}

class EsmoClient:
    def __init__(self):
        self.running = False
        self.task = None
        # Create SSL context that ignores self-signed certs
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def start(self):
        """Start the WebSocket listener in the background."""
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self._connect_loop())
        logger.info("🏥 ESMO Client service started.")

    async def stop(self):
        """Stop the WebSocket listener."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 ESMO Client service stopped.")

    async def _connect_loop(self):
        """Persistent connection loop with backoff."""
        backoff = 2
        while self.running:
            try:
                logger.debug(f"Connecting to ESMO WebSocket: {ESMO_WS_URL}")
                async with websockets.connect(ESMO_WS_URL, ssl=self.ssl_context) as websocket:
                    logger.info("✅ Connected to ESMO WebSocket!")
                    backoff = 2  # Reset backoff on successful connection
                    
                    async for message in websocket:
                        if not self.running:
                            break
                        await self._process_message(message)
            except Exception as e:
                logger.error(f"⚠️ ESMO Connection failed: {e}. Retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)  # Max backoff 60s

    async def _process_message(self, message: str):
        """Process incoming JSON message from ESMO."""
        try:
            data = json.loads(message)
            # Log raw message for debugging (remove in production if too noisy)
            logger.debug(f"📩 ESMO Message: {data}")

            # Basic Validation: Check if it looks like an exam result
            # We look for keys based on typical ESMO payload structure (inferred)
            # Adjust these keys after seeing real data!
            if not isinstance(data, dict):
                return

            # Example structure assumption:
            # {
            #   "type": "exam_result",
            #   "employee_id": "123",
            #   "card": "141432",  <-- This matches the 'Propusk: 2925' or 'ID' in screenshot
            #   "pressure": "128/74",
            #   "pulse": 79,
            #   "temp": 36.1,
            #   "result": "passed" / "failed"
            # }
            
            # Map fields (Adjust logic based on actual keys)
            # For now, we will try to extract what we can safely
            
            # --- SOURCE VALIDATION START ---
            # Try to identify the source terminal (Optional logging)
            source_ip = data.get("ip") or data.get("device_ip") or data.get("terminal_ip")
            serial = data.get("serial") or data.get("device_id")
            
            terminal_name = "Unknown"
            if source_ip and source_ip in ALLOWED_TERMINALS:
                terminal_name = ALLOWED_TERMINALS[source_ip]['name']
            elif serial:
                for ip, info in ALLOWED_TERMINALS.items():
                    if info["serial"] == serial:
                        terminal_name = info['name']
                        break
            
            if terminal_name != "Unknown":
                logger.info(f"DATA FROM: {terminal_name} ({source_ip or 'No IP'})")
            # --- SOURCE VALIDATION END ---

            # Use a separate DB session
            with SessionLocal() as db:
                # Add terminal name to data if found so it's saved correctly
                if terminal_name != "Unknown":
                    data['terminal'] = terminal_name
                self._save_exam(db, data)

        except json.JSONDecodeError:
            logger.warning(f"⚠️ Received non-JSON message: {message}")
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)

    def _save_exam(self, db: Session, data: dict):
        """Extract data and save to DB."""
        # 1. FIND EMPLOYEE
        # Look for 'employee_no' or 'card_number' in data
        employee_no = data.get("employee_no") or data.get("card") or data.get("tab_num")
        if not employee_no:
            # Try nested
            if "employee" in data and isinstance(data["employee"], dict):
                employee_no = data["employee"].get("no")
            
        if not employee_no:
            return  # Can't link to employee

        employee = db.query(Employee).filter(Employee.employee_no == str(employee_no)).first()
        if not employee:
            logger.warning(f"⚠️ Exam received for unknown employee_no: {employee_no}")
            return

        # 2. EXTRACT VITALS
        pressure = data.get("pressure", "")
        systolic, diastolic = None, None
        if "/" in str(pressure):
            try:
                parts = str(pressure).split("/")
                systolic = int(parts[0])
                diastolic = int(parts[1])
            except:
                pass

        pulse = data.get("pulse")
        temp = data.get("temperature")
        
        # Result parsing
        raw_result = data.get("result", "unknown")
        result_status = "passed" if str(raw_result).lower() in ["passed", "ok", "true", "allowed"] else "failed"
        
        # Override if explicitly "denied"
        if "deny" in str(raw_result).lower() or "forbid" in str(raw_result).lower():
            result_status = "failed"

        # 3. SAVE
        exam = MedicalExam(
            employee_id=employee.id,
            terminal_name=data.get("terminal", "Unknown"),
            result=result_status,
            pressure_systolic=systolic,
            pressure_diastolic=diastolic,
            pulse=int(pulse) if pulse else None,
            temperature=float(temp) if temp else None,
            alcohol_mg_l=float(data.get("alcohol", 0.0)),
            timestamp=datetime.now()
        )
        db.add(exam)
        db.commit()
        logger.info(f"✅ Saved exam for {employee.first_name} {employee.last_name}: {result_status}")

esmo_client = EsmoClient()
