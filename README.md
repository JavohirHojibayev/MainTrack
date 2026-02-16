# MineTrack - Automated Mining Personnel Tracking System

MineTrack is a comprehensive system designed to track personnel within mining zones using Hikvision turnstiles and biometric data. It features a real-time dashboard, automated event logging, and integration with external HR/Payroll systems.

## Features

*   **Real-time Dashboard:** Monitor the number of employees inside the mine.
*   **Turnstile Integration:** Webhook-based integration with Hikvision access control terminals.
*   **Employee Management:** Track employee statuses (Inside/Outside) and shifts.
*   **Reporting:** Generate reports on "Ghost" employees (Inside but not scanned out) and blocked attempts.
*   **Multi-language Support:** Uzbek, Russian, English.

## Tech Stack

*   **Backend:** Python (FastAPI), SQLAlchemy, PostgreSQL
*   **Frontend:** React (Vite), Material UI
*   **Database:** PostgreSQL

## Setup Instructions

### Prerequisites

*   Python 3.8+
*   Node.js 18+
*   PostgreSQL 14+

### 1. Backend Setup

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```

2.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  Configure environment variables:
    *   Copy `.env.example` to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Update `.env` with your database credentials and secret keys.

5.  Run database migrations:
    ```bash
    alembic upgrade head
    ```

6.  (Optional) Seed initial data:
    ```bash
    python seed_admin.py
    ```

7.  Start the backend server:
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```

### 2. Frontend Setup

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```

2.  Install dependencies:
    ```bash
    npm install
    ```

3.  Configure environment variables:
    *   Copy `.env.example` to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Ensure `VITE_API_URL` points to your backend (default: `http://localhost:8000/api/v1`).

4.  Start the development server:
    ```bash
    npm run dev
    ```

## Hikvision Integration

To receive events from Hikvision turnstiles:

1.  Log in to the turnstile's web interface (iVMS).
2.  Go to **Configuration -> Network -> Advanced Settings -> HTTP Listening**.
3.  Set the destination IP to your MineTrack server IP (e.g., `192.168.0.3`).
4.  Set Port to `8000`.
5.  Set Request URL to `/api/v1/hikvision/webhook`.
6.  Save and reboot the device.

## License

Private and Confidential.
