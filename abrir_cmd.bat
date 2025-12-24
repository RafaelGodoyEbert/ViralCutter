@echo off

REM Vai para a pasta onde está o .bat
cd /d "%~dp0"

REM Ativa o ambiente virtual criado pelo uv
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo Ambiente virtual .venv ativado.
) else (
    echo AVISO: Ambiente virtual .venv nao encontrado.
    echo Execute install_dependencies.bat primeiro.
)

REM Abre um CMD interativo e mantém aberto
cmd /k
