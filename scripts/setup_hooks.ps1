# Install git pre-push hook for AI log submission (Windows PowerShell).
# Run once after cloning:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1 [-Watcher]
#
#   -Watcher   Also start log_opencode_watch.py in the background, so user
#              prompts typed in OpenCode are auto-logged in real time,
#              without waiting for a `git push`. PID is written to
#              .git/hooks/.opencode-watcher.pid.

param(
    [switch]$Watcher
)

$ErrorActionPreference = 'Stop'

$HookFile = '.git/hooks/pre-push'
$PidFile  = '.git/hooks/.opencode-watcher.pid'

# Git on Windows runs hooks via Git Bash, so the hook body must be bash.
$HookBody = @'
#!/usr/bin/env bash
# Pre-push: sweep recent Antigravity / OpenCode prompts, then submit AI logs.
bash scripts/_pyrun.sh scripts/log_antigravity.py --auto || true
bash scripts/_pyrun.sh scripts/log_opencode.py --auto || true
bash scripts/_pyrun.sh scripts/submit_log.py || true
exit 0
'@

Set-Content -Path $HookFile -Value $HookBody -Encoding UTF8 -NoNewline
Write-Host "[ai-log] Git pre-push hook installed."

if (-not (Test-Path .ai-log)) { New-Item -ItemType Directory -Path .ai-log | Out-Null }
if (-not (Test-Path .ai-log/.gitkeep)) { New-Item -ItemType File -Path .ai-log/.gitkeep | Out-Null }

if ($Watcher) {
    $AlreadyRunning = $false
    if (Test-Path $PidFile) {
        $existingPid = Get-Content $PidFile -ErrorAction SilentlyContinue
        if ($existingPid -and (Get-Process -Id $existingPid -ErrorAction SilentlyContinue)) {
            $AlreadyRunning = $true
            Write-Host "[ai-log] Watcher already running (pid $existingPid)."
        }
    }
    if (-not $AlreadyRunning) {
        $python = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $python) { $python = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
        if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
        if (-not $python) { throw "No Python interpreter found in PATH." }
        $proc = Start-Process -FilePath $python `
            -ArgumentList @('scripts\log_opencode_watch.py') `
            -WorkingDirectory (Get-Location) `
            -RedirectStandardOutput '.ai-log\watcher.log' `
            -RedirectStandardError '.ai-log\watcher.log' `
            -WindowStyle Hidden -PassThru
        Set-Content -Path $PidFile -Value $proc.Id -Encoding UTF8
        Write-Host "[ai-log] Watcher started (pid $($proc.Id), log: .ai-log\watcher.log)."
        Write-Host "[ai-log] Stop with: Stop-Process -Id $($proc.Id)"
    }
}

Write-Host "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."
