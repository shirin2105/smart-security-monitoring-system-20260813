# Chạy CV pipeline lặp liên tục: xử lý clip rồi chạy lại, đẩy sự kiện vào back-end.
# Usage: powershell -File scripts/run_cv_loop.ps1 [-Clip tests/clips/walking_people.mp4] [-Frames 400] [-Interval 5]

param(
    [string]$Clip = "tests/clips/walking_people.mp4",
    [int]$Frames = 400,
    [int]$Interval = 5
)

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$ClipAbs = Join-Path $Root $Clip

# Import `app` package yêu cầu cwd là root repo
Set-Location $Root

if (-not (Test-Path $ClipAbs)) {
    Write-Host "Clip không tồn tại: $ClipAbs" -ForegroundColor Red
    exit 1
}

Write-Host "=== CV Pipeline Loop ===" -ForegroundColor Cyan
Write-Host "Clip: $Clip | Frames/clip: $Frames | Nghỉ giữa vòng: ${Interval}s" -ForegroundColor Yellow

$script = @"
import sys
sys.path.insert(0, '.')
from app.cv.multi_camera_runner import MultiCameraRunner

cfg = {
    'camera_id': 'cam_01',
    'source_uri': r'$($Clip -replace '\\', '/')',
    'source_type': 'SIMULATED',
    'inference_fps': 5.0,
    'enabled': True,
}
r = MultiCameraRunner(camera_configs=[cfg])
res = r.run(max_frames=$Frames)
for k, v in res.items():
    n = len(v.get('events', []))
    print(f'[loop] {k}: {v["status"]} ({n} events)')
"@

while ($true) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Chạy pipeline..." -ForegroundColor Green
    & $Python -c $script 2>&1 | Where-Object { $_ -notmatch "^(Ultralytics|YOLO|Model|Download)" }
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Xong vòng. Nghỉ ${Interval}s..." -ForegroundColor DarkGray
    Start-Sleep -Seconds $Interval
}
