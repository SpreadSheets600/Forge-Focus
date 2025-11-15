# FocusForge Launcher
# Double-click this file to start FocusForge!

Write-Host "⚡ Starting FocusForge..." -ForegroundColor Cyan
Write-Host ""

# Check if UV is available
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "❌ UV not found. Installing UV..." -ForegroundColor Yellow
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "C:\Users\maity\.local\bin;$env:Path"
}

# Navigate to project directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "📦 Checking dependencies..." -ForegroundColor Cyan
uv sync --quiet

Write-Host "🚀 Launching FocusForge..." -ForegroundColor Green
Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  ⚡ FocusForge - Stay Focused, Build Great Things" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════" -ForegroundColor Magenta
Write-Host ""
Write-Host "💡 Tips:" -ForegroundColor Yellow
Write-Host "  • Install browser extension from /extension/chrome" -ForegroundColor White
Write-Host "  • API runs on http://localhost:8765" -ForegroundColor White
Write-Host "  • Press Ctrl+C to stop" -ForegroundColor White
Write-Host ""

uv run python -m focusforge.main
