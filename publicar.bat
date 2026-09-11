@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Publicar base do monitor

echo.
echo  == MONITOR PC E SC ALMOXARIFADO ==
echo  Gerando a base a partir dos arquivos da pasta dados e publicando no GitHub.
echo.

if not exist "dados\mata121.xlsx" goto faltando
if not exist "dados\mata110.xlsx" goto faltando

python gerar_dados.py
if errorlevel 1 goto erro

echo.
git add -A
git diff --cached --quiet && goto semmudanca

for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set HOJE=%%a/%%b/%%c
git commit -m "atualiza base %HOJE%"
if errorlevel 1 goto erro

git push
if errorlevel 1 goto erropush

echo.
echo  Pronto. Em cerca de um minuto os aparelhos que estiverem com o monitor
echo  aberto trocam para a base nova sozinhos.
goto fim

:faltando
echo  Nao encontrei os arquivos do Protheus.
echo  Salve as exportacoes na pasta "dados" com estes nomes:
echo     dados\mata121.xlsx      pedidos de compra
echo     dados\mata110.xlsx      solicitacoes de compra
echo     dados\PROD_EM_PP.xlsx   ponto de pedido (opcional)
goto fim

:semmudanca
echo  A base gerada e igual a que ja esta publicada. Nada a enviar.
goto fim

:erropush
echo  O envio falhou. Verifique a conexao e se voce esta logado no GitHub.
goto fim

:erro
echo  Algo deu errado no passo acima. Leia a mensagem e tente de novo.

:fim
echo.
pause
