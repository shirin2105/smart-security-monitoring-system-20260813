@echo off
setlocal

cd /d "%~dp0\..\.."
set "PYTHON_EXE=third_party\deimv2\.python311\python.exe"
set "WEBCAM_APP=devtools\webcam_cv_test\app.py"
set "OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS=0"

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Python runtime not found: %PYTHON_EXE%
  pause
  exit /b 1
)

netstat -ano | findstr /R /C:":5000 .*LISTENING" >nul
if not errorlevel 1 (
  echo [INFO] A web server is already using port 5000.
  start "" "http://127.0.0.1:5000"
  exit /b 0
)

echo [INFO] Starting Phase 8.5 webcam test with CUDA when available...
echo [INFO] Keep this window open. Press Ctrl+C to stop camera and web.

start "" /min powershell.exe -NoProfile -WindowStyle Hidden -Command ^
  "Start-Sleep -Seconds 4; Start-Process 'http://127.0.0.1:5000'"

"%PYTHON_EXE%" "%WEBCAM_APP%"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] Webcam server stopped with exit code %EXIT_CODE%.
  pause
)

exit /b %EXIT_CODE%
