@echo off
setlocal
pushd "%~dp0"

echo.
echo  == MONITOR PC E SC ALMOXARIFADO ==
echo  Ligando a publicacao automatica de 5 em 5 minutos.
echo.

where pythonw >nul 2>&1
if errorlevel 1 (
  echo  Nao encontrei o Python. Instale em python.org marcando "Add python.exe to PATH".
  goto fim
)

for /f "delims=" %%p in ('where pythonw') do set PYW=%%p

schtasks /create /tn "Monitor PC e SC" /tr "\"%PYW%\" \"%~dp0verificar.py\" --sempre" /sc minute /mo 5 /f >nul
if errorlevel 1 goto erro

echo  Pronto. De 5 em 5 minutos o computador faz sozinho o mesmo que o publicar.bat:
echo  gera a base a partir da pasta dados e envia para o GitHub.
echo  Nao abre janela nenhuma e nao precisa de clique.
echo.
echo  Passadas sem novidade nao geram commit, entao nao poluem o historico.
echo  O que aconteceu em cada publicacao fica em publicacao.log.
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
