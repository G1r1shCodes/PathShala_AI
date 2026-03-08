$ErrorActionPreference = "Stop"

Write-Host "Starting AWS Lambda packaging for microservices..." -ForegroundColor Cyan

if (Test-Path "lambda_pkg") { Remove-Item -Recurse -Force "lambda_pkg" }
if (Test-Path "deployment.zip") { Remove-Item -Force "deployment.zip" }
New-Item -ItemType Directory -Force -Path "lambda_pkg" | Out-Null

Write-Host "Downloading Linux dependencies for AWS environment..." -ForegroundColor Yellow
# We only need google-generativeai, boto3, and twilio for the standalone handlers
pip install google-generativeai boto3 twilio urllib3==1.26.18 -t lambda_pkg --platform manylinux2014_x86_64 --only-binary=:all: --upgrade

Write-Host "Copying AWS Lambda handler files..." -ForegroundColor Yellow
Copy-Item lambda_generate.py -Destination lambda_pkg\
Copy-Item lambda_call_webhook.py -Destination lambda_pkg\
Copy-Item lambda_call_respond.py -Destination lambda_pkg\
Copy-Item lambda_call_generate.py -Destination lambda_pkg\
Copy-Item ncert.json -Destination lambda_pkg\
if (Test-Path ".env") { Copy-Item .env -Destination lambda_pkg\ }

Write-Host "Zipping deployment package..." -ForegroundColor Yellow
Set-Location lambda_pkg
Compress-Archive -Path * -DestinationPath ..\deployment.zip -Force
Set-Location ..

Write-Host "Done! deployment.zip is ready for AWS Lambda upload." -ForegroundColor Green
