@echo off
echo ==========================================
echo Instalando uv (Gerenciador de pacotes rapido Python)...
echo ==========================================
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

echo.
echo ==========================================
echo Criando ambiente virtual (.venv)...
echo ==========================================
:: Tenta usar o uv do PATH. Se falhar, pode ser necessario reiniciar o terminal.
uv venv

echo.
echo ==========================================
echo Instalando dependencias do requirements.txt...
echo ==========================================
:: Ativa o venv temporariamente para o install (uv gerencia isso automaticamente se detectar o venv, mas vamos garantir)
:: Se o uv venv criou a pasta .venv, o uv pip install vai usar ela por padrao se estiver na raiz.
uv pip install -r requirements.txt

echo.
echo ==========================================
echo Concluido!
echo ==========================================
pause
