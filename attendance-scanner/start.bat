@echo off
echo ============================================
echo   AttendScan - Student Attendance Scanner
echo ============================================
echo.

REM Check .env
if not exist "backend\.env" (
    echo [ERROR] backend\.env not found!
    echo.
    echo  1. Copy backend\.env.example to backend\.env
    echo  2. Fill in your SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
    echo.
    pause
    exit /b 1
)

echo [1/2] Starting Backend (FastAPI) on http://localhost:8000 ...
start "AttendScan-Backend" cmd /k "cd backend && pip install -r requirements.txt -q && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 4 /nobreak >nul

echo [2/2] Starting Frontend (React) on https://localhost:5173 ...
start "AttendScan-Frontend" cmd /k "cd frontend && npm install && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo   COMPUTER:  https://localhost:5173
echo   API Docs:  http://localhost:8000/docs
echo ============================================
echo.
echo  NOTE: Browser will show a security warning
echo  for HTTPS. Click "Advanced" then "Proceed"
echo  (it is safe -- self-signed certificate)
echo.
echo ============================================
echo   PHONE ACCESS (no install needed):
echo ============================================
echo.
echo   Open a NEW terminal and run:
echo   cd frontend
echo   npx localtunnel --port 5173
echo.
echo   Then open the https://xxx.loca.lt link
echo   on your phone. Camera will work!
echo.
pause
