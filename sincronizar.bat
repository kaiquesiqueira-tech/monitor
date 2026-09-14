@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Sincronizacao automatica - Monitor PC e SC
python sincronizar.py
pause
