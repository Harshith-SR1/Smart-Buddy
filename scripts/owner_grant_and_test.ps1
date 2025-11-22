<#
Owner-run script: grant role, enable APIs, list models, and run the example.

USAGE (run while signed in as a human owner / IAM Admin):
1. Open PowerShell as the owner account (run `gcloud auth login` if needed).
2. From repo root run: `powershell -ExecutionPolicy Bypass -File .\scripts\owner_grant_and_test.ps1`

This script will:
- set the project to `dark1745light`
- grant `roles/aiplatform.user` to the service account `smart-buddy-sa@dark1745light.iam.gserviceaccount.com`
- enable required APIs (non-billing APIs only)
- display the IAM binding
- list available models (uses the currently-authenticated account's access token)
- optionally set ADC env var to a provided path and run the example

Note: This script does NOT require the service account credentials to be the active credentials. It must be run by a human account with OWNER or IAM Admin privileges.
#>

param(
    [string]$ProjectId = "dark1745light",
    [string]$ServiceAccountEmail = "smart-buddy-sa@dark1745light.iam.gserviceaccount.com",
    [string]$ServiceAccountKeyPath = "C:\Users\Harshith S R\credentials\smart-buddy-sa-key.json",
    [switch]$RunExample
)

function FailIf([string]$msg){ Write-Error $msg; exit 1 }

# Check gcloud
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)){
    FailIf "gcloud CLI not found in PATH. Install Cloud SDK and try again: https://cloud.google.com/sdk/docs/install"
}

Write-Host "Using gcloud from:" (Get-Command gcloud).Path

# Show active account
$activeAccount = & gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
if (-not $activeAccount){
    Write-Host "No active gcloud account. Running interactive login..."
    & gcloud auth login || FailIf "gcloud auth login failed"
    $activeAccount = & gcloud auth list --filter=status:ACTIVE --format="value(account)"
}

Write-Host "Active gcloud account: $activeAccount"

if ($activeAccount -like "*gserviceaccount*"){
    Write-Warning "The active account appears to be a service account. You must run this script while signed in as a human owner or IAM admin. Run 'gcloud auth login' with a human account and re-run this script."
}

# Set project
Write-Host "Setting project to $ProjectId"
& gcloud config set project $ProjectId | Out-Null

# Grant role
Write-Host "Granting roles/aiplatform.user to $ServiceAccountEmail (this requires owner/IAM permission)"
& gcloud projects add-iam-policy-binding $ProjectId `
  --member="serviceAccount:$ServiceAccountEmail" `
  --role="roles/aiplatform.user" | Out-Null

Write-Host "Waiting 5 seconds for IAM propagation..."
Start-Sleep -Seconds 5

# Confirm IAM binding
Write-Host "Verifying IAM binding for $ServiceAccountEmail"
& gcloud projects get-iam-policy $ProjectId --flatten="bindings[]" --filter="bindings.members:serviceAccount:$ServiceAccountEmail" --format="json" | ConvertFrom-Json | ConvertTo-Json -Depth 6

# Enable required non-billing APIs
Write-Host "Enabling required non-billing APIs (generativelanguage, serviceusage, cloudresourcemanager)"
& gcloud services enable generativelanguage.googleapis.com serviceusage.googleapis.com cloudresourcemanager.googleapis.com --project=$ProjectId

# List models using the currently-authenticated account's token
Write-Host "Fetching access token for current account and listing models (may return 403 if roles not yet propagated)"
$token = & gcloud auth print-access-token
if (-not $token){ Write-Warning "Could not acquire access token" } else {
    try{
        $models = Invoke-RestMethod -Headers @{ Authorization = "Bearer $token" } -Uri "https://generativelanguage.googleapis.com/v1beta2/models" -Method Get -ErrorAction Stop
        Write-Host "Models list (JSON):"
        $models | ConvertTo-Json -Depth 6
    } catch {
        Write-Warning "Model list request failed: $($_.Exception.Message)"
        if ($_.Exception.Response){
            $r = $_.Exception.Response.GetResponseStream(); $sr = New-Object System.IO.StreamReader($r); $body = $sr.ReadToEnd();
            Write-Host "HTTP response body:`n$body"
        }
    }
}

# Optionally run the example using ADC from the provided service account JSON
if ($RunExample){
    if (-not (Test-Path $ServiceAccountKeyPath)){
        FailIf "Service account key not found at $ServiceAccountKeyPath. Update the path or place the key there."
    }

    Write-Host "Setting GOOGLE_APPLICATION_CREDENTIALS to: $ServiceAccountKeyPath"
    $env:GOOGLE_APPLICATION_CREDENTIALS = $ServiceAccountKeyPath

    Write-Host "Activating virtual environment (if present)"
    $venvActivate = Join-Path -Path (Get-Location) -ChildPath ".venv\Scripts\Activate.ps1"
    if (Test-Path $venvActivate){
        Write-Host "Sourcing venv activation: $venvActivate"
        & $venvActivate
    } else {
        Write-Warning "Virtual environment activation script not found at $venvActivate. Ensure dependencies are installed in your environment before running the example."
    }

    Write-Host "Running example: python .\examples\gemini_example.py"
    & python .\examples\gemini_example.py
}

Write-Host "Script finished. If any step failed, copy the output and share it so I can help further."
