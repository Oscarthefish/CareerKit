#!/bin/bash
#
# CareerKit launcher — starts Ollama, the backend API, and the frontend,
# then opens the app in your browser. Close the window (or press Ctrl-C)
# to shut everything back down.
#
set -uo pipefail

ROOT="/Users/jason/Desktop/Projects/CareerKit"
BACKEND_PORT=8001
FRONTEND_PORT=3000
OLLAMA_URL="http://localhost:11434"
LOG_DIR="/tmp/careerkit"

# Make sure Homebrew tools (node, npm, ollama) are on PATH even when launched
# from Finder with a minimal environment.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

mkdir -p "$LOG_DIR"

BACKEND_PID=""
FRONTEND_PID=""
OLLAMA_PID=""

cleanup() {
  echo ""
  echo "Shutting down CareerKit..."
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null
  [[ -n "$BACKEND_PID" ]]  && kill "$BACKEND_PID" 2>/dev/null
  [[ -n "$OLLAMA_PID" ]]   && kill "$OLLAMA_PID" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

wait_for() {  # wait_for <url> <seconds>
  local url="$1" timeout="$2" i=0
  while (( i < timeout )); do
    curl -sf -o /dev/null "$url" && return 0
    sleep 1; ((i++))
  done
  return 1
}

echo "=== Starting CareerKit ==="

# 1. Ollama (local AI) ---------------------------------------------------------
if curl -sf -o /dev/null "$OLLAMA_URL/api/tags"; then
  echo "Ollama already running."
elif command -v ollama >/dev/null 2>&1; then
  echo "Starting Ollama..."
  ollama serve >"$LOG_DIR/ollama.log" 2>&1 &
  OLLAMA_PID=$!
  wait_for "$OLLAMA_URL/api/tags" 30 && echo "Ollama ready." \
    || echo "WARNING: Ollama did not come up — AI features may not work (see $LOG_DIR/ollama.log)."
else
  echo "WARNING: 'ollama' not found. Install from https://ollama.com — AI features will not work."
fi

# 2. Backend API -------------------------------------------------------------
if curl -sf -o /dev/null "http://localhost:$BACKEND_PORT/api/health"; then
  echo "Backend already running on :$BACKEND_PORT."
else
  echo "Starting backend on :$BACKEND_PORT..."
  ( cd "$ROOT/backend" && exec venv/bin/uvicorn app.main:app --port "$BACKEND_PORT" ) \
    >"$LOG_DIR/backend.log" 2>&1 &
  BACKEND_PID=$!
  wait_for "http://localhost:$BACKEND_PORT/api/health" 30 && echo "Backend ready." \
    || echo "WARNING: backend did not come up (see $LOG_DIR/backend.log)."
fi

# 3. Frontend --------------------------------------------------------------
if curl -sf -o /dev/null "http://localhost:$FRONTEND_PORT"; then
  echo "Frontend already running on :$FRONTEND_PORT."
else
  echo "Starting frontend on :$FRONTEND_PORT..."
  ( cd "$ROOT/frontend" && exec npm run dev ) >"$LOG_DIR/frontend.log" 2>&1 &
  FRONTEND_PID=$!
  wait_for "http://localhost:$FRONTEND_PORT" 60 && echo "Frontend ready." \
    || echo "WARNING: frontend did not come up (see $LOG_DIR/frontend.log)."
fi

# 4. Open the app --------------------------------------------------------------
open "http://localhost:$FRONTEND_PORT"

if [[ -z "$BACKEND_PID$FRONTEND_PID$OLLAMA_PID" ]]; then
  echo "Everything was already running. Nothing to keep open — exiting."
  exit 0
fi

echo ""
echo "CareerKit is running at http://localhost:$FRONTEND_PORT"
echo "Logs: $LOG_DIR/  —  Close this window or press Ctrl-C to stop."
wait
