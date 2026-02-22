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
echo CONFIGURACAO DE PLACA DE VIDEO
echo ==========================================
echo Qual e a sua Placa de Video?
echo [1] NVIDIA (Instala com aceleracao CUDA - Mais rapido)
echo [2] AMD / Nenhuma (Ou se nao souber - Instala versao normal)
set /p gpu_choice="Escolha (1/2): "

if "%gpu_choice%"=="1" (
    echo.
    echo Instalando PyTorch e ONNX para NVIDIA...
    uv pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
    uv pip install onnxruntime-gpu==1.20.1
    echo Instalando LLaMA C++ para NVIDIA...
    uv pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124
) else (
    echo.
    echo Instalando PyTorch e ONNX para AMD/CPU...
    uv pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
    uv pip install onnxruntime==1.20.1
    echo Instalando LLaMA C++ normal (Requer C++ Build Tools)...
    uv pip install llama-cpp-python
)

echo.
echo ==========================================
echo Instalando TODAS as dependencias (INCLUINDO MODELOS LOCAIS LLM)
echo Atenção: Processo mais demorado. Requer C++ Build Tools.
echo ==========================================
uv pip install -r requirements.txt

echo.
echo ==========================================
echo Concluido! O ViralCutter esta pronto para rodar Modelos Locais.
echo ==========================================
pause
