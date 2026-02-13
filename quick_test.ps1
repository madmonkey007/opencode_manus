# Quick start and test
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host "Starting OpenCode server..."
$proc = Start-Process -FilePath 'python' -ArgumentList 'run_server.py' -WorkingDirectory 'D:\manus\opencode' -PassThru -WindowStyle Minimized
Write-Host "PID: $($proc.Id)"

Write-Host "Waiting for startup..."
Start-Sleep -Seconds 8

Write-Host "Testing connection..."
try {
    $response = Invoke-WebRequest -Uri 'http://localhost:8088/' -UseBasicParsing -TimeoutSec 10
    Write-Host "HTTP $($response.StatusCode)" -ForegroundColor Green

    $api = Invoke-WebRequest -Uri 'http://localhost:8088/openapi.json' -UseBasicParsing -TimeoutSec 5
    $content = $api.Content | ConvertFrom-Json
    Write-Host "Routes: $($content.paths.Count)" -ForegroundColor Cyan

    Write-Host ""
    Write-Host "SUCCESS! Server is running." -ForegroundColor Green
    Write-Host "Open browser: http://localhost:8088?use_new_api=true"
} catch {
    Write-Host "FAILED: $_" -ForegroundColor Red
}
