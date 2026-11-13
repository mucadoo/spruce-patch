@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0link-gdrive.ps1"
if errorlevel 1 echo.
pause
