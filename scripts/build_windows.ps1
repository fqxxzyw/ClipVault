param([switch]$OneFile)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m venv .venv
    } else {
        python -m venv .venv
    }
    if ($LASTEXITCODE -ne 0) { throw "Could not create .venv. Install Python 3.11+." }
}
& .\.venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11+ is required." }
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
$BuildArgs = @("scripts/build.py")
if ($OneFile) { $BuildArgs += "--onefile" }
& .\.venv\Scripts\python.exe @BuildArgs
if ($LASTEXITCODE -ne 0) { throw "Build failed" }
& .\.venv\Scripts\python.exe scripts/smoke_bundle.py
if ($LASTEXITCODE -ne 0) { throw "Packaged smoke test failed" }
