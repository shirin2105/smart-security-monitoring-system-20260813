# Run MVP end-to-end: CV pipeline -> back-end API -> frontend
# Script khởi chạy toàn bộ hệ thống Smart Security Monitoring System MVP

param(
    [string]$BackendPort = "8000",
    [string]$FrontendPort = "5173"
)

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    $Python = "python"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       Smart Security Monitoring System MVP (P-176)         " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Start Back-end API
Write-Host "[1/3] Khởi động Back-end API (Port $BackendPort)..." -ForegroundColor Yellow
Push-Location (Join-Path $Root "back-end")
$backend = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", $BackendPort -PassThru -NoNewWindow
Pop-Location

# 2. Check Backend Health
Write-Host "[2/3] Kiểm tra trạng thái Backend..." -ForegroundColor Yellow
$healthy = $false
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($res.status -eq "ok") {
            $healthy = $true
            Write-Host "      ✓ Backend API đã sẵn sàng! (Status: OK)" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $healthy) {
    Write-Host "      ! Cảnh báo: Backend chưa phản hồi /health, tiếp tục khởi động Frontend..." -ForegroundColor DarkYellow
}

# 3. Start Frontend UI
Write-Host "[3/3] Khởi động Frontend Web Application (Port $FrontendPort)..." -ForegroundColor Yellow
Push-Location (Join-Path $Root "front-end")
$frontend = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev", "--", "--port", $FrontendPort -PassThru -NoNewWindow
Pop-Location

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  HỆ THỐNG MVP ĐANG CHẠY THÀNH CÔNG!                       " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  🌐 Frontend Web UI : http://localhost:$FrontendPort" -ForegroundColor White
Write-Host "  ⚡ Back-end API    : http://localhost:$BackendPort" -ForegroundColor White
Write-Host "  📖 Swagger Docs    : http://localhost:$BackendPort/docs" -ForegroundColor White
Write-Host "  🔑 Tài khoản mẫu   : guard / guard123 hoặc manager / manager123" -ForegroundColor White
Write-Host ""
Write-Host "  📹 Để chạy luồng sự kiện CV thật (Multi-camera):" -ForegroundColor Cyan
Write-Host "     $Python -m app.cv.multi_camera_runner" -ForegroundColor Gray
Write-Host ""
Write-Host "  🧪 Để chạy Demo CLI kiểm thử sự cố mẫu:" -ForegroundColor Cyan
Write-Host "     python -m app.cv.demo_cli" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Dừng dịch vụ thủ công: Stop-Process -Id $($backend.Id),$($frontend.Id) -Force" -ForegroundColor DarkGray
Write-Host ""
