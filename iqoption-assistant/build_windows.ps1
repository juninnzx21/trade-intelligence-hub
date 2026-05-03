param()

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$distRoot = Join-Path $projectRoot "dist"
$appRoot = Join-Path $distRoot "iqoption-assistant"
$specPath = Join-Path $projectRoot "iqoption-assistant.spec"
$readmePath = Join-Path $projectRoot "README.md"
$envPath = Join-Path $projectRoot ".env"
$envExamplePath = Join-Path $projectRoot ".env.example"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$storageRoot = Join-Path $appRoot "storage"
$storageLogs = Join-Path $storageRoot "logs"
$sourceIntegrityManifest = Join-Path $projectRoot "storage\integrity_manifest.json"
$distIntegrityManifest = Join-Path $storageRoot "integrity_manifest.json"
$shortcutPath = Join-Path $appRoot "IQ Option Assistant.lnk"
$exePath = Join-Path $appRoot "iqoption-assistant.exe"

$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "Build iniciado em $projectRoot"

if (Test-Path $distRoot) {
    Remove-Item $distRoot -Recurse -Force
}

$buildDir = Join-Path $projectRoot "build"
if (Test-Path $buildDir) {
    Remove-Item $buildDir -Recurse -Force
}

& $pythonCmd -m PyInstaller --noconfirm --clean $specPath

if (-not (Test-Path $appRoot)) {
    throw "Diretorio final nao encontrado em $appRoot"
}

Copy-Item $readmePath (Join-Path $appRoot "README.md") -Force
Copy-Item $envExamplePath (Join-Path $appRoot ".env.example") -Force

if (Test-Path $envPath) {
    Copy-Item $envPath (Join-Path $appRoot ".env") -Force
} else {
    Copy-Item $envExamplePath (Join-Path $appRoot ".env") -Force
}

New-Item -ItemType Directory -Force -Path $storageRoot | Out-Null
New-Item -ItemType Directory -Force -Path $storageLogs | Out-Null
New-Item -ItemType File -Force -Path (Join-Path $storageRoot ".gitkeep") | Out-Null
New-Item -ItemType File -Force -Path (Join-Path $storageLogs ".gitkeep") | Out-Null

& $pythonCmd main.py --write-integrity
if (-not (Test-Path $sourceIntegrityManifest)) {
    throw "Manifesto de integridade nao encontrado em $sourceIntegrityManifest"
}
Copy-Item $sourceIntegrityManifest $distIntegrityManifest -Force

$env:IQASSISTANT_BASE_DIR = $appRoot
& $pythonCmd main.py --write-integrity
Remove-Item Env:IQASSISTANT_BASE_DIR -ErrorAction SilentlyContinue
if (-not (Test-Path $distIntegrityManifest)) {
    throw "Manifesto de integridade nao foi gerado no pacote dist em $distIntegrityManifest"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = $appRoot
$shortcut.Description = "Abrir IQ Option Assistant"
$shortcut.Save()

Write-Host "Build finalizado em $appRoot"
Write-Host "Executavel: $exePath"
Write-Host "Atalho: $shortcutPath"
Write-Host "Manifesto: $distIntegrityManifest"
