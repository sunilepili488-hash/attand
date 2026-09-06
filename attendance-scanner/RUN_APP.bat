@echo off
cls
echo.
echo  === AttendScan - App Start ===
echo.
if not exist "%~dp0backend\.env" (
  echo [ERROR] .env file nahi mili!
  echo Pehle SETUP_ENV.bat run karo.
  pause
  exit /b
)
echo [1/2] Backend start ho raha hai...
start "Backend" cmd /k "cd /d %~dp0backend && pip install -r requirements.txt -q && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 5 /nobreak >nul
echo [2/2] Frontend start ho raha hai...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm install && npm run dev"
timeout /t 5 /nobreak >nul
echo.
echo  ==========================================
echo   Computer pe kholo:
echo   https://localhost:5173
echo   (Warning aaye to: Advanced then Proceed)
echo  ==========================================
echo.
echo   PHONE ke liye - naya CMD kholo aur type karo:
echo   cd %~dp0frontend
echo   npx localtunnel --port 5173
echo.
pause