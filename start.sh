#!/bin/bash

# Terminate background processes on exit
trap 'kill $(jobs -p)' EXIT

echo "🍳 Starting Chef Assist..."

# 1. Start Python FastAPI Backend
echo "🚀 Launching Backend API on http://127.0.0.1:8000..."
cd backend
.venv/bin/python main.py &
BACKEND_PID=$!
cd ..

# 2. Wait for backend to be ready
sleep 2

# 3. Start React Frontend
echo "💻 Launching React Frontend..."
cd frontend
npm run dev -- --host 127.0.0.1 &
FRONTEND_PID=$!
cd ..

echo "--------------------------------------------------------"
echo "✨ Chef Assist is fully up and running!"
echo "👉 Frontend URL: http://127.0.0.1:5173"
echo "👉 Backend API:  http://127.0.0.1:8000"
echo "--------------------------------------------------------"
echo "Press Ctrl+C to stop both servers."

# Keep script running to monitor processes
wait
