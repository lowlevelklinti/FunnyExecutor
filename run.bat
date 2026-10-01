@echo off
cd /d "%~dp0src"
set "PY=%~dp0.venv\Scripts\python.exe"
if exist "%PY%" (
  "%PY%" main.py
) else (
  python main.py
)
if errorlevel 1 pause