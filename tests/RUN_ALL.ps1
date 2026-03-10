# 一键执行所有调研脚本

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "OpenCode 性能优化调研 - 一键执行脚本"  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# 检查Python环境
Write-Host "[1/4] 检查Python环境..."  -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✅ Python版本: $pythonVersion"  -ForegroundColor Green
} catch {
    Write-Host "  ❌ Python未安装或不在PATH中"  -ForegroundColor Red
    exit 1
}

# 安装依赖
Write-Host "`n[2/4] 安装依赖..."  -ForegroundColor Yellow
try {
    pip install -r tests/requirements.txt -q
    Write-Host "  ✅ 依赖安装完成"  -ForegroundColor Green
} catch {
    Write-Host "  ❌ 依赖安装失败"  -ForegroundColor Red
    exit 1
}

# Day 1: 性能测试
Write-Host "`n========================================"  -ForegroundColor Cyan
Write-Host "Day 1: 性能测试"  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "`n请确保:"  -ForegroundColor Yellow
Write-Host "  1. 当前FastAPI服务器在端口8000运行"  -ForegroundColor Yellow
Write-Host "  2. opencode web服务器在端口8888运行"  -ForegroundColor Yellow
Write-Host ""

$continue = Read-Host "是否继续? (Y/N)"
if ($continue -ne "Y" -and $continue -ne "y") {
    Write-Host "跳过Day 1测试"  -ForegroundColor Yellow
} else {
    Write-Host "`n执行性能测试..."  -ForegroundColor Green
    try {
        python tests/benchmark/benchmark.py
        Write-Host "`n✅ Day 1 完成"  -ForegroundColor Green
    } catch {
        Write-Host "`n❌ Day 1 失败: $_"  -ForegroundColor Red
    }
}

# Day 2: API兼容性
Write-Host "`n========================================"  -ForegroundColor Cyan
Write-Host "Day 2: API兼容性检查"  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

$continue = Read-Host "是否继续Day 2? (Y/N)"
if ($continue -ne "Y" -and $continue -ne "y") {
    Write-Host "跳过Day 2测试"  -ForegroundColor Yellow
} else {
    Write-Host "`n执行API兼容性检查..."  -ForegroundColor Green
    try {
        python tests/api_compatibility/api_check.py
        Write-Host "`n✅ Day 2 完成"  -ForegroundColor Green
    } catch {
        Write-Host "`n❌ Day 2 失败: $_"  -ForegroundColor Red
    }
}

# Day 3: 最终分析
Write-Host "`n========================================"  -ForegroundColor Cyan
Write-Host "Day 3: 最终分析和决策"  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

$continue = Read-Host "是否继续Day 3? (Y/N)"
if ($continue -ne "Y" -and $continue -ne "y") {
    Write-Host "跳过Day 3分析"  -ForegroundColor Yellow
} else {
    Write-Host "`n执行最终分析..."  -ForegroundColor Green
    try {
        python tests/analysis/final_analysis.py
        Write-Host "`n✅ Day 3 完成"  -ForegroundColor Green
    } catch {
        Write-Host "`n❌ Day 3 失败: $_"  -ForegroundColor Red
    }
}

# 总结
Write-Host "`n========================================"  -ForegroundColor Cyan
Write-Host "调研执行完成"  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""
Write-Host "查看结果:"  -ForegroundColor Yellow
Write-Host "  - 测试日志: tests/logs/benchmark.log"  -ForegroundColor White
Write-Host "  - 测试结果: tests/results/"  -ForegroundColor White
Write-Host "  - 生成的报告: reports/"  -ForegroundColor White
Write-Host ""
Write-Host "关键报告:"  -ForegroundColor Yellow
Write-Host "  - reports/day1_performance.md"  -ForegroundColor White
Write-Host "  - reports/day2_api_compatibility.md"  -ForegroundColor White
Write-Host "  - reports/FINAL_DECISION.md"  -ForegroundColor White
Write-Host ""
