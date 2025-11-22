<#
.SYNOPSIS
  Download a reviewer model to the `models/reviewers` directory with optional checksum verification.

.NOTES
  This script intentionally does NOT download anything by default. Provide a URL and expected checksum.
  Run only after you have confirmed licensing and disk size requirements.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$Url,

    [Parameter(Mandatory=$true)]
    [string]$OutFile,

    [string]$Checksum = $null,

    [switch]$Force
)

$dest = Join-Path -Path (Split-Path -Parent $MyInvocation.MyCommand.Path) -ChildPath $OutFile

if (Test-Path $dest -and -not $Force) {
    Write-Host "Destination file already exists: $dest`nUse -Force to overwrite." -ForegroundColor Yellow
    exit 1
}

Write-Host "About to download model from: $Url" -ForegroundColor Cyan
Write-Host "Destination: $dest" -ForegroundColor Cyan

$confirm = Read-Host "Proceed with download? Type 'yes' to continue"
if ($confirm -ne 'yes') {
    Write-Host "Aborting download." -ForegroundColor Yellow
    exit 1
}

try {
    Write-Host "Downloading..."
    Invoke-WebRequest -Uri $Url -OutFile $dest -UseBasicParsing -Verbose
} catch {
    Write-Host "Download failed: $_" -ForegroundColor Red
    exit 1
}

if ($Checksum) {
    Write-Host "Verifying checksum..."
    $alg = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($dest)
    $hash = [BitConverter]::ToString($alg.ComputeHash($stream)).Replace('-', '').ToLowerInvariant()
    $stream.Close()
    if ($hash -ne $Checksum.ToLower()) {
        Write-Host "Checksum mismatch: expected $Checksum but got $hash" -ForegroundColor Red
        exit 1
    }
    Write-Host "Checksum OK" -ForegroundColor Green
}

Write-Host "Model downloaded to $dest" -ForegroundColor Green
