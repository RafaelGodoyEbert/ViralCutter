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
echo Instalando TODAS as dependencias (INCLUINDO MODELOS LOCAIS LLM)
echo Atenção: Processo mais demorado. Requer C++ Build Tools.
echo ==========================================
uv pip install -r requirements_advanced_LocalLLM.txt

echo.
echo ==========================================
echo Concluido! O ViralCutter esta pronto para rodar Modelos Locais.
echo ==========================================
pause
