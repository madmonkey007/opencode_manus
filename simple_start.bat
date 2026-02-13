@echo off
cd /d D:\manus\opencode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8088 --log-level info
