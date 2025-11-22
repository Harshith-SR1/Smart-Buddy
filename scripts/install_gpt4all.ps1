<#
Install helper for gpt4all prebuilt binary and a small quantized model on Windows.
USAGE (from repo root, with venv activated):
  powershell -ExecutionPolicy Bypass -File .\scripts\install_gpt4all.ps1

This script will:
- Create `models/gpt4all/` directory
- Download a prebuilt gpt4all Windows binary and a small ggml model into that directory
- Verify that the binary runs and prints version/help

New flags:
- `-MaxRetries <n>`: retry transient downloads up to `n` times (default 3).
- `-RetryDelay <s>`: base retry delay in seconds (exponential backoff, default 5).
- `-VerboseOutput`: enable extra progress messages during downloads.
Checksum behavior:
- If a companion checksum asset is found it will be downloaded and used to verify SHA256.
- If no checksum asset is available, verification is skipped with a warning (you may verify manually).

NOTES:
- This script downloads third-party artifacts from their release pages. Verify URLs before running.
- By default this script uses the lightweight "gpt4all-lora-quantized" style small models if available.
- If you prefer a different model, update the $modelUrl variable accordingly.
#>

param(
    [string]$RepoRoot = (Get-Location).Path,
    [string]$OutDir = "models\gpt4all",
    [switch]$SkipDownload,
    [switch]$ForceRun,
    [int]$MaxRetries = 3,
    [int]$RetryDelay = 5,
    [switch]$VerboseOutput
    ,[switch]$UseBitsTransfer
)

$ErrorActionPreference = 'Stop'

# Helper: download with retries + exponential backoff and simple progress messages
function Invoke-WebRequestWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$OutFile
    )

    $attempt = 0
    while ($true) {
        try {
            $attempt++
            if ($VerboseOutput) { Write-Host "[Download] Attempt $attempt -> $Uri" }
            Invoke-WebRequest -Uri $Uri -OutFile $OutFile -UseBasicParsing -ErrorAction Stop
            if ($VerboseOutput) { Write-Host "[Download] Saved $OutFile" }
            break
        } catch {
            Write-Warning "Download failed (attempt $attempt): $($_.Exception.Message)"
            if ($attempt -ge $MaxRetries) {
                throw "Failed to download $Uri after $attempt attempts"
            }
            $delay = [int]([math]::Min($RetryDelay * [math]::Pow(2, $attempt - 1), 60))
            Write-Host "Retrying in $delay seconds..."
            Start-Sleep -Seconds $delay
        }
    }
}

# Wrapper: prefer Start-BitsTransfer when requested and available, otherwise fall back to Invoke-WebRequestWithRetry
function Invoke-Download {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$OutFile
    )

    if ($UseBitsTransfer) {
        try {
            if (Get-Command -Name Start-BitsTransfer -ErrorAction SilentlyContinue) {
                if ($VerboseOutput) { Write-Host "[BitsTransfer] Downloading $Uri -> $OutFile" }
                # Start-BitsTransfer supports resuming and shows progress in PowerShell
                Start-BitsTransfer -Source $Uri -Destination $OutFile -ErrorAction Stop
                if ($VerboseOutput) { Write-Host "[BitsTransfer] Saved $OutFile" }
                return
            } else {
                Write-Warning "Start-BitsTransfer not available in this PowerShell session; falling back to web request."
            }
        } catch {
            Write-Warning "Start-BitsTransfer failed: $($_.Exception.Message). Falling back to web request."
        }
    }

    # Fallback to the retrying Invoke-WebRequest helper
    Invoke-WebRequestWithRetry -Uri $Uri -OutFile $OutFile
}

$absOut = Join-Path -Path $RepoRoot -ChildPath $OutDir
if (-not (Test-Path $absOut)){
    Write-Host "Creating directory $absOut"
    New-Item -ItemType Directory -Path $absOut | Out-Null
} else {
    Write-Host "Using existing directory $absOut"
}

if ($SkipDownload){ Write-Host "Skipping download as requested"; exit 0 }

Write-Host "Downloading gpt4all prebuilt binary and model into: $absOut"
Write-Host "Note: If you see an ExecutionPolicy error, run PowerShell as Administrator and use:`n  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`nOr run this script with `-ExecutionPolicy Bypass` to bypass for this session.`nUse `-ForceRun` to attempt executing the downloaded binary for verification.`n"

Write-Host "Attempting to discover the latest gpt4all release via GitHub API..."

# Query GitHub Releases API for latest release
$apiUrl = 'https://api.github.com/repos/nomic-ai/gpt4all/releases/latest'
try{
    $json = Invoke-RestMethod -Uri $apiUrl -Headers @{ 'User-Agent' = 'gpt4all-installer-script' } -ErrorAction Stop
} catch {
    Write-Warning "Failed to fetch release info from GitHub: $($_.Exception.Message)"
    Write-Host "Falling back to placeholder URLs. You may need to edit this script manually."
    return
}

# Find Windows executable asset (prefer x86_64 win64)
# assets from release
$assets = $json.assets
$winAsset = $null
foreach ($a in $assets) {
    $n = $a.name.ToLower()
    if ($n -match 'win' -and ($n -match '.exe' -or $n -match 'win64' -or $n -match 'windows')){
        $winAsset = $a
        break
    }
}

# Find a ggml/.bin model asset in the release assets (some releases bundle models)
$modelAsset = $null
foreach ($a in $assets) {
    $n = $a.name.ToLower()
    if ($n -match 'ggml' -or $n -match '\.bin$' -or $n -match '\.gguf$'){
        $modelAsset = $a
        break
    }
}

if ($winAsset) {
    $binaryUrl = $winAsset.browser_download_url
    $binaryPath = Join-Path $absOut $winAsset.name
    Write-Host "Found Windows binary asset: $($winAsset.name)"
    if (-not (Test-Path $binaryPath)){
        Write-Host "Downloading binary from $binaryUrl ..."
        Invoke-Download -Uri $binaryUrl -OutFile $binaryPath
        Write-Host "Saved binary to $binaryPath"
    } else { Write-Host "Binary already present: $binaryPath" }
    # look for companion checksum asset (.sha256, .sha256sum)
    $checksumAsset = $assets | Where-Object { $_.name -match '\.(sha256|sha256sum|sha256.txt)$' } | Select-Object -First 1
    if ($checksumAsset) {
        $csUrl = $checksumAsset.browser_download_url
        $csPath = Join-Path $absOut $checksumAsset.name
        if (-not (Test-Path $csPath)){
            Write-Host "Downloading checksum asset $($checksumAsset.name) ..."
            Invoke-Download -Uri $csUrl -OutFile $csPath
        }
        # simple SHA256 verify if possible
        try{
            $expected = Get-Content $csPath | Select-Object -First 1
            if ($expected -match '([a-fA-F0-9]{64})'){
                $exp = $Matches[1]
                try{
                    $actual = (Get-FileHash -Path $binaryPath -Algorithm SHA256).Hash
                    if ($exp -ieq $actual){ Write-Host "Binary checksum OK" } else { Write-Warning "Binary checksum mismatch" }
                } catch { Write-Warning "Failed to compute binary checksum: $($_.Exception.Message)" }
            }
        } catch { Write-Warning "Checksum verification failed: $($_.Exception.Message)" }
    }
    else {
        Write-Warning "No checksum asset found for binary; checksum verification will be skipped."
    }
} else {
    Write-Warning "No Windows binary asset found in latest release. Please download a prebuilt binary manually and place it in $absOut"
}

if ($modelAsset) {
    $modelUrl = $modelAsset.browser_download_url
    $modelPath = Join-Path $absOut $modelAsset.name
    Write-Host "Found model asset: $($modelAsset.name)"
    if (-not (Test-Path $modelPath)){
        Write-Host "Downloading model from $modelUrl ..."
            Invoke-Download -Uri $modelUrl -OutFile $modelPath
        Write-Host "Saved model to $modelPath"
    } else { Write-Host "Model already present: $modelPath" }
    # checksum check if companion exists
    $modelCs = $assets | Where-Object { $_.name -match '\.(sha256|sha256sum|sha256.txt)$' } | Select-Object -First 1
    if ($modelCs) {
        $mcsPath = Join-Path $absOut $modelCs.name
        if (-not (Test-Path $mcsPath)){
            Invoke-Download -Uri $modelCs.browser_download_url -OutFile $mcsPath
        }
        try{
            $expected = Get-Content $mcsPath | Select-Object -First 1
            if ($expected -match '([a-fA-F0-9]{64})'){
                $exp = $Matches[1]
                try{
                    $actual = (Get-FileHash -Path $modelPath -Algorithm SHA256).Hash
                    if ($exp -ieq $actual){ Write-Host "Model checksum OK" } else { Write-Warning "Model checksum mismatch" }
                } catch { Write-Warning "Failed to compute model checksum: $($_.Exception.Message)" }
            }
        } catch { Write-Warning "Model checksum verification failed: $($_.Exception.Message)" }
    } else {
        Write-Warning "No checksum asset found for model; checksum verification will be skipped."
    }
} else {
    Write-Warning "No model asset embedded in release. Attempting to download a recommended small model from gpt4all.io..."
    # Recommended fallback model URL (maintained by gpt4all project site). Update if needed.
    $fallbackModelUrl = 'https://gpt4all.io/models/ggml-gpt4all-j-v1.2-jazzy.bin'
    $modelPath = Join-Path $absOut 'ggml-gpt4all-jazzy.bin'
    try{
            if (-not (Test-Path $modelPath)){
            Write-Host "Downloading fallback model from $fallbackModelUrl ..."
            Invoke-Download -Uri $fallbackModelUrl -OutFile $modelPath
            Write-Host "Saved fallback model to $modelPath"
        } else { Write-Host "Fallback model already present: $modelPath" }
    } catch {
        Write-Warning "Failed to download fallback model: $($_.Exception.Message)"
        Write-Warning "Please download a ggml model manually (e.g., from the gpt4all models page) and place it in $absOut"
    }
}

# Final checks
if (Get-ChildItem -Path $absOut | Where-Object { $_.Name -match '\.exe$' } ){
    Write-Host "gpt4all binary found in $absOut"
    # attempt to run the binary to verify (optional)
    $exe = Get-ChildItem -Path $absOut | Where-Object { $_.Name -match '\.exe$' } | Select-Object -First 1
    if ($exe -and $ForceRun){
        try{
            Write-Host "Executing $($exe.FullName) --version to verify binary..."
            & $exe.FullName --version
        } catch { Write-Warning "Binary execution failed: $($_.Exception.Message)" }
    }
} else { Write-Warning "No .exe found in $absOut; please add a Windows binary there." }

if (Get-ChildItem -Path $absOut | Where-Object { $_.Name -match '\.(bin|gguf|bin.gz)$' } ){
    Write-Host "Model file found in $absOut"
} else { Write-Warning "No model file found in $absOut; please add a ggml model file there." }

Write-Host "Install script finished. If any downloads failed, check the script output and consider downloading assets manually from: https://github.com/nomic-ai/gpt4all/releases/latest or https://gpt4all.io/models/"