$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendPath = Join-Path $projectRoot "frontend"
$targetPath = "/domains/roboiqopition.juninnzxtec.com.br/public_html"

if (-not (Test-Path $targetPath)) {
    throw "Caminho de deploy nao encontrado: $targetPath"
}

Push-Location $frontendPath
try {
    npm install
    npm run build
    Remove-Item (Join-Path $targetPath "*") -Recurse -Force -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $frontendPath "dist\*") $targetPath -Recurse -Force
}
finally {
    Pop-Location
}
