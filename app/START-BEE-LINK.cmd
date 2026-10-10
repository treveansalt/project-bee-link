@echo off
set "BEELINK_BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
echo Starting Bee Link. Keep this window open while using the local logger.
if exist "%BEELINK_BUNDLED_PYTHON%" (
  "%BEELINK_BUNDLED_PYTHON%" "%~dp0server.py" --open-browser
) else (
  python "%~dp0server.py" --open-browser
)
pause
