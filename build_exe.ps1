$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    & $VenvPython -m PyInstaller --noconfirm .\pubg_match_analyzer.spec
} else {
    python -m PyInstaller --noconfirm .\pubg_match_analyzer.spec
}
