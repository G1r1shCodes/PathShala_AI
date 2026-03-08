# build_layer_fixed.ps1
$ErrorActionPreference = "Stop"

Write-Host "Building AWS Lambda Layer for Python 3.12 (x86_64)..." -ForegroundColor Cyan

if (Test-Path "layer_pkg") { Remove-Item -Recurse -Force "layer_pkg" }
if (Test-Path "pathshala_layer.zip") { Remove-Item -Force "pathshala_layer.zip" }

# AWS Lambda Layers MUST have this exact folder structure
New-Item -ItemType Directory -Force -Path "layer_pkg\python" | Out-Null

Write-Host "Downloading Pre-compiled Linux Binaries..." -ForegroundColor Yellow
# We must explicitly specify python_version to force pip to grab the Python 3.12 wheels, 
# otherwise it might grab the wheels for the local Windows Python version (e.g. 3.10)
pip install google-generativeai boto3 twilio urllib3==1.26.18 grpcio -t layer_pkg\python --platform manylinux2014_x86_64 --python-version 3.12 --only-binary=:all:

Write-Host "Zipping Layer..." -ForegroundColor Yellow
Set-Location layer_pkg
Compress-Archive -Path python -DestinationPath ..\pathshala_layer.zip -Force
Set-Location ..

Write-Host "Done! Upload 'pathshala_layer.zip' to AWS Lambda Layers." -ForegroundColor Green
