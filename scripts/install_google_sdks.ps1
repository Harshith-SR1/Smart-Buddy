<#
PowerShell helper script to download installers for Google Cloud SDK and provide guidance for Google ADK.
Run this script in an elevated PowerShell session if required. This script attempts non-interactive install where possible,
but some steps may require manual interaction or confirm prompts.

DO NOT ADD API KEYS OR CREDENTIALS TO THIS SCRIPT.
#>

Write-Output "Starting SDK helper script..."

# Attempt to install via Chocolatey if available (quiet)
if (Get-Command choco -ErrorAction SilentlyContinue) {
    Write-Output "Chocolatey detected — installing googlecloudsdk via choco (may require admin)..."
    choco install googlecloudsdk -y
} else {
    Write-Output "Chocolatey not found. Downloading Google Cloud SDK installer..."
    $temp = $env:TEMP
    $installer = Join-Path $temp "GoogleCloudSDKInstaller.exe"
    $url = 'https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe'
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    Write-Output "Downloaded to $installer"
    Write-Output "Running installer (may open UI). If you want a fully headless install, consider Chocolatey or manual steps."
    Start-Process -FilePath $installer -Wait
}

Write-Output "Google Cloud SDK installer step finished."

Write-Output "---\nGoogle ADK / AI Dev Kit note:\nIf you mean 'Google ADK' or a specific AI developer kit (e.g., SDK for Gemini / PaLM or Android Dev Kit), follow provider docs.\nThis script doesn't auto-install ADKs because there are multiple products with different installers.\nRefer to docs: https://cloud.google.com/sdk and https://developers.google.com/" 

Write-Output "Script complete. Configure auth separately using 'gcloud init' when ready."