# Deploy Smart Buddy to Google Cloud Run (PowerShell)
# Prerequisites: gcloud CLI installed and authenticated

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$ProjectId = "smart-buddy-prod",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-central1",
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "smart-buddy"
)

# Override defaults with environment variables if present
if ($env:GCP_PROJECT_ID) { $ProjectId = $env:GCP_PROJECT_ID }
if ($env:GCP_REGION) { $Region = $env:GCP_REGION }

$ErrorActionPreference = "Stop"

Write-Host "[DEPLOY] Smart Buddy to Google Cloud Run" -ForegroundColor Cyan
Write-Host "   Project: $ProjectId"
Write-Host "   Region: $Region"
Write-Host ""

# Check if gcloud is installed
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] gcloud CLI not found. Install from https://cloud.google.com/sdk/docs/install" -ForegroundColor Red
    exit 1
}

# Check authentication
Write-Host "[AUTH] Checking authentication..." -ForegroundColor Yellow
gcloud auth list

# Set project
Write-Host "[PROJECT] Setting project to $ProjectId..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# Enable required APIs
Write-Host "[API] Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create secret for API key (if not exists)
Write-Host "[SECRET] Setting up API key secret..." -ForegroundColor Yellow
gcloud secrets describe google-api-key 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    $apiKey = $env:GOOGLE_API_KEY
    if (-not $apiKey) {
        Write-Host "[WARNING] GOOGLE_API_KEY not set. Skipping secret creation." -ForegroundColor Yellow
        Write-Host "   Create manually: echo -n 'YOUR_API_KEY' | gcloud secrets create google-api-key --data-file=-"
    } else {
        $apiKey | gcloud secrets create google-api-key --data-file=-
        Write-Host "[OK] Secret created" -ForegroundColor Green
    }
} else {
    Write-Host "[OK] Secret already exists" -ForegroundColor Green
}

# Build and deploy using Cloud Build
Write-Host "[BUILD] Building and deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --source . `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --memory 2Gi `
    --cpu 2 `
    --timeout 300 `
    --min-instances 1 `
    --max-instances 10 `
    --port 8000 `
    --set-env-vars "ENVIRONMENT=production,LOG_LEVEL=INFO" `
    --update-secrets "GOOGLE_API_KEY=google-api-key:latest" `
    --quiet

# Get service URL
$serviceUrl = gcloud run services describe $ServiceName --region $Region --format 'value(status.url)'

Write-Host ""
Write-Host "[SUCCESS] Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Service URL: $serviceUrl" -ForegroundColor Cyan
Write-Host "Metrics Dashboard: $serviceUrl/metrics" -ForegroundColor Cyan
Write-Host "Health Check: $serviceUrl/health" -ForegroundColor Cyan
Write-Host "Audit Console: $serviceUrl/audit" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test the deployment:" -ForegroundColor Yellow
Write-Host "  Invoke-WebRequest -Uri $serviceUrl/health" -ForegroundColor White
Write-Host ""
