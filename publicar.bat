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
dir /b "dados\SALDO*.xls*" >nul 2>&1 && (for /f "delims=" %%s in ('dir /b "dados\SALDO*.xls*"') do echo  [ok] dados\%%s) || echo  [ ] nenhum arquivo SALDO: a aba Reposicao fica vazia
if "%FALTA%"=="1" goto faltando

echo.
echo  Sincronizando com o GitHub...
git fetch origin
for /f "delims=" %%r in ('git rev-parse --abbrev-ref HEAD') do set RAMO=%%r
git merge --no-edit -X ours origin/%RAMO%
if errorlevel 1 goto conflito

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
if errorlevel 1 (
  echo  Envio recusado. Alguem publicou nesse meio tempo; juntando e tentando de novo...
  git fetch origin
  git merge --no-edit -X ours origin/%RAMO%
  git push
  if errorlevel 1 goto erropush
)

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

:conflito
echo.
echo  Nao consegui juntar o que esta no GitHub com o que esta aqui.
echo  Rode "git merge --abort" e depois "git pull" uma vez nesta pasta.
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
