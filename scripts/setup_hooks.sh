#!/usr/bin/env bash
# Install git pre-push hook for AI log submission (POSIX / Git Bash).
# Run once after cloning: bash scripts/setup_hooks.sh [--watcher]
#
#   --watcher   Also start log_opencode_watch.py in the background, so user
#               prompts typed in OpenCode are auto-logged in real time,
#               without waiting for a `git push`. The watcher writes a PID
#               file to .git/hooks/.opencode-watcher.pid.
set -e

WITH_WATCHER=0
for arg in "$@"; do
  case "$arg" in
    --watcher) WITH_WATCHER=1 ;;
    *) echo "[ai-log] Unknown flag: $arg" >&2; exit 1 ;;
  esac
done

HOOK_FILE=".git/hooks/pre-push"

cat > "$HOOK_FILE" <<'EOF'
#!/usr/bin/env bash
# Pre-push: sweep recent Antigravity / OpenCode prompts, then submit AI logs.
# Uses the cross-platform Python launcher so it works whether the user
# has python3, python, or only the `py` launcher (Windows).
bash scripts/_pyrun.sh scripts/log_antigravity.py --auto || true
bash scripts/_pyrun.sh scripts/log_opencode.py --auto || true
bash scripts/_pyrun.sh scripts/submit_log.py || true
exit 0  # Never block push, even if either step fails
EOF

chmod +x "$HOOK_FILE"
chmod +x scripts/_pyrun.sh 2>/dev/null || true
echo "[ai-log] Git pre-push hook installed."

mkdir -p .ai-log
touch .ai-log/.gitkeep

if [ "$WITH_WATCHER" = "1" ]; then
  PID_FILE=".git/hooks/.opencode-watcher.pid"
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "[ai-log] Watcher already running (pid $(cat "$PID_FILE"))."
  else
    nohup bash scripts/_pyrun.sh scripts/log_opencode_watch.py \
      >.ai-log/watcher.log 2>&1 &
    echo $! > "$PID_FILE"
    echo "[ai-log] Watcher started (pid $(cat "$PID_FILE"), log: .ai-log/watcher.log)."
    echo "[ai-log] Stop with: kill \$(cat $PID_FILE)"
  fi
fi

echo "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."
