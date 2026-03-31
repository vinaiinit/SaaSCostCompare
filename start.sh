#!/bin/bash

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Kill anything on ports 8000 and 3000
lsof -ti :8000 | xargs kill -9 2>/dev/null
lsof -ti :3000 | xargs kill -9 2>/dev/null

echo "Starting backend on http://localhost:8000 ..."
cd "$ROOT/backend"
"$ROOT/.venv/bin/python" -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:3000 ..."
cd "$ROOT/frontend"
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

echo ""
echo "Both servers running. Open http://localhost:3000"
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" INT TERM
wait
