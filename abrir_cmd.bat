@echo off

REM Vai para a pasta onde está o .bat
cd /d "%~dp0"

REM Inicializa o conda
call "%USERPROFILE%\miniconda3\Scripts\activate.bat"

REM Ativa o ambiente local
call conda activate ./env

REM Abre um CMD interativo e mantém aberto
cmd /k
