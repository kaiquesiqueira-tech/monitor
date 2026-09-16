@echo off
setlocal
pushd "%~dp0"

echo.
echo  == MONITOR PC E SC ALMOXARIFADO ==
echo  Ligando a verificacao automatica da pasta dados, de 2 em 2 minutos.
echo.

where pythonw >nul 2>&1
if errorlevel 1 (
  echo  Nao encontrei o Python. Instale em python.org marcando "Add python.exe to PATH".
  goto fim
)

for /f "delims=" %%p in ('where pythonw') do set PYW=%%p

schtasks /create /tn "Monitor PC e SC" /tr "\"%PYW%\" \"%~dp0verificar.py\"" /sc minute /mo 2 /f >nul
if errorlevel 1 goto erro

echo  Pronto. De agora em diante o computador confere a pasta dados sozinho,
echo  de 2 em 2 minutos, sem janela nenhuma aberta.
echo.
echo  Salve as exportacoes do Protheus em "dados" e pode fechar tudo.
echo  O que aconteceu em cada passada fica em publicacao.log.
echo.
echo  Para desligar: desagendar.bat
goto fim

:erro
echo  Nao consegui criar a tarefa. Tente abrir este arquivo com o botao direito,
echo  opcao "Executar como administrador".

:fim
echo.
popd
pause
