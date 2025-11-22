# PowerShell script to build and run the Smart Buddy Docker image on Windows
# Usage (PowerShell):
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
#   .\examples\run_in_docker.ps1

$ImageName = 'smart-buddy:local'
Write-Host "Building Docker image $ImageName..."
docker build -t $ImageName .
Write-Host "Running container and mounting ./models to /app/models..."
docker run --rm -it -v "${PWD}\models:/app/models" $ImageName
