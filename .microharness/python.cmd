@echo off
REM Lanzador cmd.exe: reenvia a python.ps1 con PowerShell 7+ o Windows PowerShell.
setlocal
where pwsh >nul 2>nul
if %ERRORLEVEL%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0python.ps1" %*
  exit /b %ERRORLEVEL%
)
where powershell >nul 2>nul
if %ERRORLEVEL%==0 (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0python.ps1" %*
  exit /b %ERRORLEVEL%
)
echo Error: se necesita pwsh o powershell para .microharness\python.cmd >&2
exit /b 2
