$ErrorActionPreference = 'Stop'
$bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$runtimePython = if (Test-Path -LiteralPath $bundledPython) { $bundledPython } else { 'python' }
Write-Host 'Starting Bee Link at http://127.0.0.1:8765. Press Ctrl+C to stop.'
& $runtimePython (Join-Path $PSScriptRoot 'server.py')
