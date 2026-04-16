$ErrorActionPreference = 'Stop'

$opensslPath = 'C:\Program Files\OpenSSL\bin\openssl.exe'
$projectRoot = Split-Path -Parent $PSScriptRoot
$certDir = Join-Path $projectRoot '.cert'
$certPath = Join-Path $certDir 'localhost-cert.pem'
$keyPath = Join-Path $certDir 'localhost-key.pem'

if (-not (Test-Path $opensslPath)) {
    throw 'OpenSSL was not found at C:\Program Files\OpenSSL\bin\openssl.exe. Install OpenSSL.Light first.'
}

New-Item -ItemType Directory -Force -Path $certDir | Out-Null

& $opensslPath req -x509 -nodes -newkey rsa:2048 `
    -keyout $keyPath `
    -out $certPath `
    -days 365 `
    -subj '/CN=localhost' `
    -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'

certutil -user -addstore Root $certPath | Out-Null

Write-Host "Created and trusted localhost development certificate at $certPath"