#!/bin/bash
# Ensure frontend/dist exists (committed to git)
if [ ! -d "frontend/dist" ]; then
  echo "frontend/dist not found, checking git..."
  ls frontend/dist 2>/dev/null || echo "frontend/dist not found locally either"
fi
echo "Frontend dist contents:"
ls frontend/dist/ 2>/dev/null | head -5 || echo "empty or missing"
echo "Starting server..."
python3 main.py
