# Run Smart Buddy locally on localhost:8000
# This script starts the Flask development server for local testing

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [int]$Port = 8000
)

Write-Host "[LOCALHOST] Starting Smart Buddy on http://127.0.0.1:$Port" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-Host "[WARNING] Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
Write-Host "[VENV] Activating virtual environment..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"

# Install dependencies if needed
if (-not (Test-Path ".venv\Lib\site-packages\flask")) {
    Write-Host "[INSTALL] Installing dependencies..." -ForegroundColor Yellow
    pip install -e .
}

# Check for GOOGLE_API_KEY
if (-not $env:GOOGLE_API_KEY) {
    Write-Host "[WARNING] GOOGLE_API_KEY not set. Set it with:" -ForegroundColor Yellow
    Write-Host '  $env:GOOGLE_API_KEY = "your-api-key"' -ForegroundColor White
    Write-Host ""
}

Write-Host "[SERVER] Starting Flask development server..." -ForegroundColor Green
Write-Host ""
Write-Host "Available Endpoints:" -ForegroundColor Cyan
Write-Host "  Health Check:      http://127.0.0.1:$Port/health" -ForegroundColor White
Write-Host "  Metrics Dashboard: http://127.0.0.1:$Port/metrics" -ForegroundColor White
Write-Host "  Audit Console:     http://127.0.0.1:$Port/audit" -ForegroundColor White
Write-Host "  Chat API:          POST http://127.0.0.1:$Port/chat" -ForegroundColor White
Write-Host "  User Tasks:        http://127.0.0.1:$Port/tasks/<user_id>" -ForegroundColor White
Write-Host "  User Events:       http://127.0.0.1:$Port/events/<user_id>" -ForegroundColor White
Write-Host ""
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Set Flask environment
$env:FLASK_APP = "server_flask.py"
$env:FLASK_ENV = "development"

# Run server
python server_flask.py
