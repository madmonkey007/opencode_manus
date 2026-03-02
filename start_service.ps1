$ErrorActionPreference = "Continue"
Set-Location "D:\manus\opencode"
Write-Host "Starting OpenCode service on port 8089..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8089
