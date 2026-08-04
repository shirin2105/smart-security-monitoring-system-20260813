#!/usr/bin/env bash
# Cross-platform Python launcher for AI log hooks.
# Prefers the project venv, then python3 → python → py -3 on PATH; on Windows,
# falls back to common Python install locations because Git Bash launched by
# some hooks gets a stripped PATH that omits the Windows Python directory.
# Designed to be sourced or called as: bash scripts/_pyrun.sh <script> [args...]
#
# Exits 0 silently if no Python is found — hooks must never block the AI tool.
set -u

# A candidate must actually run, not merely exist on PATH. Windows ships
# "App execution alias" stubs for python3/python under
# AppData/Local/Microsoft/WindowsApps: command -v finds them, but they only
# print a Microsoft Store install notice and exit non-zero, which silently
# broke every hook on machines without the Store Python.
works() {
  "$@" -c "" >/dev/null 2>&1
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd)"

PY=""
# Project venv first: hooks run without the venv activated, and the venv is
# the interpreter that has this project's dependencies (python-dotenv, which
# submit_log.py needs to read AI_LOG_API_KEY out of .env).
for cand in "$REPO_ROOT/.venv/Scripts/python.exe" "$REPO_ROOT/.venv/bin/python"; do
  if [ -x "$cand" ] && works "$cand"; then PY="$cand"; break; fi
done

if [ -z "$PY" ]; then
  if works python3; then PY=python3
  elif works python; then PY=python
  elif works py -3; then PY="py -3"
  else
    # PATH lookup failed — probe standard Windows install locations.
    shopt -s nullglob 2>/dev/null || true
    for cand in \
      /c/Users/*/AppData/Local/Programs/Python/Python*/python.exe \
      "/c/Program Files/Python"*/python.exe \
      "/c/Program Files (x86)/Python"*/python.exe \
      /c/Python*/python.exe; do
      if [ -x "$cand" ] && works "$cand"; then PY="$cand"; break; fi
    done
    shopt -u nullglob 2>/dev/null || true
    [ -n "$PY" ] || exit 0
  fi
fi

# shellcheck disable=SC2086
exec $PY "$@"
