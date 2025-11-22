<#
PowerShell helper to install CPU-only local LLM dependencies and test download
USAGE (from repo root, with your venv activated):
  powershell -ExecutionPolicy Bypass -File .\scripts\install_local_llm.ps1

This script will:
- Ensure you have pip available in the active venv
- Install CPU-only PyTorch and Transformers
- Run a quick test script to download and run `distilgpt2` locally

Notes:
- On Windows this uses the official PyTorch CPU wheels. Adjust if you have GPU and want CUDA.
- The first run will download model weights (~256MB).
#>

# Fail fast
$ErrorActionPreference = 'Stop'

Write-Host "Checking Python..."
if (-not (Get-Command python -ErrorAction SilentlyContinue)){
    Write-Error "python not found in PATH. Activate your venv or install Python and retry."; exit 1
}

Write-Host "Installing CPU PyTorch and Transformers (may take a few minutes)..."
# Install CPU-only torch from official index and transformers
python -m pip install --upgrade pip
python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio --upgrade
python -m pip install transformers==4.34.0

Write-Host "Creating and running a quick test to generate text with distilgpt2"
$testPy = @'
from transformers import pipeline

generator = pipeline('text-generation', model='distilgpt2')
print('Model loaded:', generator.model.__class__)
print(generator('Hello, I am testing a local model: ', max_length=80, num_return_sequences=1)[0]['generated_text'])
'@

$testFile = Join-Path -Path (Get-Location) -ChildPath 'scripts\local_test_generate.py'
Set-Content -Path $testFile -Value $testPy -Encoding UTF8

Write-Host "Running test script (this will download the model the first time)..."
python $testFile

Write-Host "Done. If the test printed generated text, the local model is working."