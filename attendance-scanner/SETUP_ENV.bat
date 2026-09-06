@echo off
cls
echo.
echo  === AttendScan - .env Setup ===
echo.
echo  Supabase se 2 values chahiye:
echo  1. https://supabase.com kholo
echo  2. Apna project kholo
echo  3. Left sidebar me Settings (gear icon)
echo  4. API tab click karo
echo  5. Project URL copy karo
echo  6. service_role key copy karo
echo.
set /p SURL=SUPABASE_URL paste karo: 
echo.
set /p SKEY=service_role KEY paste karo: 
echo.
(echo SUPABASE_URL=%SURL%
echo SUPABASE_SERVICE_ROLE_KEY=%SKEY%
echo JWT_SECRET=AttendScanKey2024XYZ987654321ABC) > "%~dp0backend\.env"
echo.
echo  Done! .env file ban gayi!
echo  Ab RUN_APP.bat double-click karo.
echo.
pause