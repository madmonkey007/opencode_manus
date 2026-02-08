@echo off
cd /d/manus/opencode/static
echo Starting frontend development server on http://localhost:3000
echo (Docker runs on port 8088, this is a separate frontend-only server)
python -m http.server 3000
