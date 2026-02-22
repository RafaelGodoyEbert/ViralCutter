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
) else (
    echo.
    echo Instalando PyTorch e ONNX para AMD/CPU...
    uv pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
    uv pip install onnxruntime==1.20.1
)

echo.
echo ==========================================
echo Instalando dependencias essenciais do requirements.txt...
echo (IAs em Nuvem / Sem Modelos Locais)
echo ==========================================
:: Ativa o venv temporariamente para o install (uv gerencia isso automaticamente se detectar o venv, mas vamos garantir)
:: Se o uv venv criou a pasta .venv, o uv pip install vai usar ela por padrao se estiver na raiz.
uv pip install -r requirements.txt

echo.
echo ==========================================
echo Concluido!
echo ==========================================
pause
