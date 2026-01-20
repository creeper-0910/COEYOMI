@echo off
setlocal enabledelayedexpansion
where uv >nul 2>&1
if errorlevel 1 (
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  set "Path=%USERPROFILE%\.local\bin;!Path!"
)
if exist "%~dp0\.venv" (
  uv run coeyomi.py
) else (
  uv sync
  uv run coeyomi.py
)
pause