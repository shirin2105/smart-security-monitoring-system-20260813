@echo off
setlocal

echo [INFO] Releasing webcam...
curl.exe --silent --max-time 3 --request POST "http://127.0.0.1:5000/stop" >nul 2>&1
ping 127.0.0.1 -n 2 >nul

set "FOUND_SERVER=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":5000 .*LISTENING"') do (
  set "FOUND_SERVER=1"
  echo [INFO] Stopping server process %%P...
  taskkill /PID %%P /T /F >nul 2>&1
)

if "%FOUND_SERVER%"=="0" (
  echo [INFO] Server is not running. Webcam is already released.
) else (
  echo [OK] Web server and webcam stopped.
)

ping 127.0.0.1 -n 3 >nul
exit /b 0
