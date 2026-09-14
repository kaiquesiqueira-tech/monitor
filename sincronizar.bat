@echo off
setlocal
pushd "%~dp0"
title Sincronizacao automatica - Monitor PC e SC
python sincronizar.py
popd
pause
