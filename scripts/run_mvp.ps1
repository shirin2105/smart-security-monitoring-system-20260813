# Run MVP end-to-end: CV pipeline -> back-end API -> frontend
# Cần 3 terminal riêng, hoặc chạy script này trong 1 terminal (Ctrl+C để dừng tất cả).

param(
    [string]$BackendPort = "8000",
    [string]$FrontendPort = "5173"
)

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host "=== P-176 MVP ===" -ForegroundColor Cyan
Write-Host "1. Back-end API (port $BackendPort)..." -ForegroundColor Yellow

# Back-end: chạy từ thư mục back-end/ vì import `app` package nội bộ
Push-Location (Join-Path $Root "back-end")
$backend = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", $BackendPort -PassThru -NoNewWindow
Pop-Location

Write-Host "2. Chờ back-end khởi động..." -ForegroundColor Yellow
Start-Sleep -Seconds 4

Write-Host "3. Frontend (port $FrontendPort)..." -ForegroundColor Yellow
Push-Location (Join-Path $Root "front-end")
$frontend = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev", "--", "--port", $FrontendPort -PassThru -NoNewWindow
Pop-Location

Write-Host ""
Write-Host "MVP đang chạy:" -ForegroundColor Green
Write-Host "  Back-end API : http://localhost:$BackendPort  (health: /health)"
Write-Host "  Frontend     : http://localhost:$FrontendPort"
Write-Host "  Login        : guard / guard123 hoặc manager / manager123"
Write-Host ""
Write-Host "CV pipeline (nguồn sự kiện thật): chạy riêng bằng lệnh:" -ForegroundColor Cyan
Write-Host "  .venv\Scripts\python.exe -m app.cv.multi_camera_runner"
Write-Host ""
Write-Host "Ctrl+C trong cửa sổ này không dừng server (Start-Process tách rời)." -ForegroundColor DarkGray
Write-Host "Dừng thủ công: Stop-Process -Id $($backend.Id),$($frontend.Id) -Force" -ForegroundColor DarkGray

$backend.Id
$frontend.Id
