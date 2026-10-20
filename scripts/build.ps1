param(
    [ValidateSet("exe", "deb", "flatpak")]
    [string]$Target = "exe"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($Target -ne "exe") {
    Write-Error "build.ps1 is intended for Windows .exe builds. Use scripts/build.sh for Linux .deb/Flatpak builds."
}

$VenvPython = Join-Path $Root ".venv-build\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    py -3 -m venv (Join-Path $Root ".venv-build")
}
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $Root "requirements-build.txt")
& $VenvPython scripts/build.py --target exe
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
