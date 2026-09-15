@echo off
setlocal
pushd "%~dp0"

echo.
echo  == MONITOR PC E SC ALMOXARIFADO ==
echo  Pasta: %CD%
echo.

set FALTA=0
if not exist "dados\mata121.xlsx" (echo  [x] falta dados\mata121.xlsx & set FALTA=1) else (echo  [ok] dados\mata121.xlsx)
if not exist "dados\mata110.xlsx" (echo  [x] falta dados\mata110.xlsx & set FALTA=1) else (echo  [ok] dados\mata110.xlsx)
if not exist "dados\PROD_EM_PP.xlsx" (echo  [x] falta dados\PROD_EM_PP.xlsx & set FALTA=1) else (echo  [ok] dados\PROD_EM_PP.xlsx)
if "%FALTA%"=="1" goto faltando

echo.
echo  Gerando a base...
python gerar_dados.py
if errorlevel 1 goto erro

echo.
echo  Enviando para o GitHub...
git add -A
git diff --cached --quiet
if not errorlevel 1 goto semmudanca

git commit -m "atualiza base"
if errorlevel 1 goto erro
git push
if errorlevel 1 goto erropush

echo.
echo  Publicado. Os aparelhos com o monitor aberto trocam de base em poucos minutos.
echo  O texto do dia para o WhatsApp esta em resumo_do_dia.txt.
goto fim

:faltando
echo.
echo  Salve as exportacoes do Protheus na pasta "dados" com os nomes marcados acima.
goto fim

:semmudanca
echo.
echo  A base gerada e igual a que ja esta publicada. Nada a enviar.
goto fim

:erropush
echo.
echo  O envio falhou. Verifique a conexao e se voce esta logado no GitHub.
goto fim

:erro
echo.
echo  Algo deu errado no passo acima. Leia a mensagem e tente de novo.

:fim
echo.
popd
pause
