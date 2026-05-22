@echo off
title Jarvis - Dev Mode
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo ERRO: Ambiente virtual nao encontrado!
    pause
    exit
)

echo Ativando ambiente virtual...
call .venv\Scripts\activate

echo ----------------------------
echo Iniciando Jarvis em modo DEV
echo ----------------------------

python agent.py dev

pause