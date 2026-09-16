@echo off
setlocal
schtasks /delete /tn "Monitor PC e SC" /f >nul 2>&1
if errorlevel 1 (echo  A verificacao automatica ja estava desligada.) else (echo  Verificacao automatica desligada.)
echo.
pause
