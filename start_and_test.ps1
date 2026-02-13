# OpenCode 服务器启动和测试脚本

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  OpenCode Server Startup and Test" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. 清理旧进程
Write-Host "[1/4] Cleaning up old Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Write-Host "  Done." -ForegroundColor Green

# 2. 启动服务器
Write-Host ""
Write-Host "[2/4] Starting OpenCode server..." -ForegroundColor Yellow
$proc = Start-Process -FilePath 'python' -ArgumentList 'run_server.py' -WorkingDirectory 'D:\manus\opencode' -PassThru -WindowStyle Minimized
Write-Host "  PID: $($proc.Id)" -ForegroundColor Cyan

# 3. 等待服务器启动
Write-Host ""
Write-Host "[3/4] Waiting for server to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

# 4. 测试连接
Write-Host ""
Write-Host "[4/4] Testing server connection..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri 'http://localhost:8088/' -UseBasicParsing -TimeoutSec 10
    Write-Host "  SUCCESS: HTTP $($response.StatusCode)" -ForegroundColor Green

    # 获取 API 信息
    $api = Invoke-WebRequest -Uri 'http://localhost:8088/openapi.json' -UseBasicParsing -TimeoutSec 5
    $content = $api.Content | ConvertFrom-Json
    Write-Host "  Total routes: $($content.paths.Count)" -ForegroundColor Cyan

    # 检查关键路由
    $routes = @($content.paths.Keys)
    $hasSession = $routes -contains '/opencode/session'
    $hasHealth = $routes -contains '/opencode/health'

    Write-Host ""
    Write-Host "  Key Routes:" -ForegroundColor Cyan
    $sessionStatus = if ($hasSession) { '[OK]' } else { '[FAIL]' }
    $healthStatus = if ($hasHealth) { '[OK]' } else { '[FAIL]' }
    Write-Host "    /opencode/session: $sessionStatus" -ForegroundColor $(if ($hasSession) { 'Green' } else { 'Red' })
    Write-Host "    /opencode/health: $healthStatus" -ForegroundColor $(if ($hasHealth) { 'Green' } else { 'Red' })

} catch {
    Write-Host "  FAILED: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Troubleshooting:" -ForegroundColor Yellow
    Write-Host "    1. Check if port 8088 is already in use" -ForegroundColor Yellow
    Write-Host "    2. Check server.log for errors" -ForegroundColor Yellow
    Write-Host "    3. Try running: python run_server.py" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Test Complete" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Browser Test URLs:" -ForegroundColor White
Write-Host "  Main:    http://localhost:8088" -ForegroundColor White
Write-Host "  New API: http://localhost:8088?use_new_api=true" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop viewing, server keeps running" -ForegroundColor Gray
Write-Host "Stop server: taskkill /F /IM python.exe" -ForegroundColor Gray
Write-Host ""

# 保持窗口打开
Read-Host "Press Enter to exit"
