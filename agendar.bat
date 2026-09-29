@echo off
setlocal
pushd "%~dp0"

echo.
echo  == MONITOR PC E SC ALMOXARIFADO ==
echo  Ligando a vigia da pasta dados, conferindo de 5 em 5 segundos.
echo.

where pythonw >nul 2>&1
if errorlevel 1 (
  echo  Nao encontrei o Python. Instale em python.org marcando "Add python.exe to PATH".
  goto fim
)

for /f "delims=" %%p in ('where pythonw') do set PYW=%%p

schtasks /create /tn "Monitor PC e SC" /tr "\"%PYW%\" \"%~dp0verificar.py\" --loop 55 --intervalo 5" /sc minute /mo 1 /f >nul
if errorlevel 1 goto erro

schtasks /run /tn "Monitor PC e SC" >nul 2>&1

echo  Pronto. A pasta dados e conferida de 5 em 5 segundos, sem janela aberta.
echo  Salvou a exportacao do Protheus, ele gera e envia para o GitHub sozinho.
echo.
echo  O Windows chama a tarefa de minuto em minuto e cada chamada cobre o minuto
echo  inteiro. Se uma execucao falhar, a do minuto seguinte assume.
echo.
echo  Gerar a base leva cerca de meio minuto por causa do arquivo de saldo, entao
echo  do momento em que voce salva ate aparecer nos celulares passa cerca de um minuto.
echo.
echo  Acompanhe em publicacao.log. Para desligar: desagendar.bat
goto fim

:erro
echo  Nao consegui criar a tarefa. Tente abrir este arquivo com o botao direito,
echo  opcao "Executar como administrador".

:fim
echo.
popd
pause
