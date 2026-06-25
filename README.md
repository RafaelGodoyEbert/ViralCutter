# ViralCutter
[![Discord](https://dcbadge.limes.pink/api/server/tAdPHFAbud)](https://discord.gg/tAdPHFAbud)<br>

**Alternativa open-source 100% gratuita, local e ilimitada ao Opus Clip**  
Transforme vídeos longos do YouTube em shorts virais otimizados para TikTok, Instagram Reels e YouTube Shorts – com IA de ponta, legendas dinâmicas, *face tracking* preciso e tradução automática. Tudo rodando na sua máquina.

[![Stars](https://img.shields.io/github/stars/RafaelGodoyEbert/ViralCutter?style=social)](https://github.com/RafaelGodoyEbert/ViralCutter/stargazers)
[![Forks](https://img.shields.io/github/forks/RafaelGodoyEbert/ViralCutter?style=social)](https://github.com/RafaelGodoyEbert/ViralCutter/network/members)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1UZKzeqjIeEyvq9nPx7s_4mU6xlkZQn_R?usp=sharing)

[English](README_en.md) • [Português](README.md)

## Por que ViralCutter é um "Game Changer"?

Esqueça assinaturas caras e limites de minutos. O ViralCutter oferece poder ilimitado no seu hardware.

| Feature | ViralCutter (Open-Source) | Opus Clip / Klap / Munch (SaaS) |
| :--- | :--- | :--- |
| **Preço** | **Gratuito e Ilimitado** | $20–$100/mês + limites de min. |
| **Privacidade** | **100% Local** (Seus dados não saem do PC) | Upload para nuvem de terceiros |
| **IA & LLM** | **Flexível**: Gemini (Free), GPT-4, **Local GGUF (Offline)** | Apenas o que eles oferecem |
| **Face Tracking** | **Split Screen (2 faces)**, Active Speaker (Exp.), Auto | Básico ou pago extra |
| **Tradução** | **Sim** (Traduza legendas p/ 10+ línguas) | Recursos limitados |
| **Edição** | **Exporta XML para Premiere Pro** (Beta) | Editor web limitado |
| **Watermark** | **ZERO** | Sim (nos planos free) |

**Resultados profissionais, privacidade total e custo zero.**

## Funcionalidades Principais 🚀

-   🤖 **Corte Viral com IA**: Identifica automaticamente os ganchos e momentos mais engajadores usando **Gemini**, **GPT-4** ou **LLMs Locais (Llama 3, DeepSeek, etc)**.
-   🗣️ **Transcrição Ultra-Precisa**: Baseado em **WhisperX** com aceleração via GPU para legendas perfeitas.
-   🎨 **Legendas Dinâmicas**: Estilo "Hormozi" com highlight palavra por palavra, cores vibrantes, emojis e total customização.
-   🎥 **Direção de Câmera Automática**:
    -   **Auto-Crop 9:16**: Transforma horizontal em vertical mantendo o foco.
    -   **Split Screen Inteligente**: Detecta 2 pessoas conversando e divide a tela automaticamente.
    -   **Active Speaker (Experimental)**: A câmera corta para quem está falando.
-   🌍 **Tradução de Vídeo**: Gere legendas traduzidas automaticamente (ex: Vídeo em Inglês -> Legenda em Português).
-   💾 **Qualidade & Controle**: Escolha a resolução (até 4K/Best), formate a saída e salve configurações de processamento.
-   ⚡ **Performance**: Transcrição com "slicing" (processa 1x, corta N vezes) e suporte a instalação ultra-rápida via `uv`.
-   🖥️ **Interface Moderna**: WebUI em Gradio, Modo Escuro, Galeria de Projetos e Editor de Legendas integrado.

## Interface Web (Inspirada no Opus Clip)
![WebUI Home](https://github.com/user-attachments/assets/ba147149-fc5f-48fc-a03c-fc86b5dc0568)
*Painel de controle intuitivo com ajustes finos de IA e renderização.*

![WebUi Library](https://github.com/user-attachments/assets/b0204e4b-0e5d-4ee4-b7b4-cac044b76c24)
*Biblioteca: Galeria estilo OpusClip e controles intuitivos*

## Instalação Local (Super Rápida ⚡)

### Pré-requisitos (Instalação "do zero")

Para rodar o ViralCutter em um computador novo, você precisa instalar os seguintes programas essenciais:

1. **Ferramentas de Build do Visual Studio (C++ Build Tools)**
   Necessário para compilar o `insightface` e evitar erros "Cpp/Visual Studio".
   - Baixe o [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
   - Abra o instalador e marque **"Desenvolvimento para Desktop com C++"** (*Desktop development with C++*).
   - Certifique-se de que *Windows 10/11 SDK* e *MSVC v143 - VS 2022 C++* estejam marcados à direita e instale. Reinicie o PC se necessário.

2. **Python (3.10.x ou 3.11.x recomendados)**
   - Baixe em [python.org/downloads](https://www.python.org/downloads/).
   - ⚠️ **MUITO IMPORTANTE:** Na primeira tela de instalação, marque a caixa **"Add Python to PATH"** no rodapé antes de clicar em instalar.

3. **FFmpeg** (Processamento de áudio/vídeo)
   - A forma mais rápida no Windows é abrir o terminal (PowerShell) como Administrador e digitar:
     `winget install ffmpeg`
   - Reinicie o terminal e digite `ffmpeg -version` para checar se instalou corretamente.

4. **Drivers da Placa de Vídeo (NVIDIA)**
   - Mantenha os drivers atualizados (via GeForce Experience ou site oficial) para usar a aceleração CUDA 12.4+.
   - **GPU NVIDIA** é fortemente recomendada para velocidade e IAs locais.

---

### Passo a Passo da Instalação

1.  **Instale as dependências via Script**
    Acesse a pasta do ViralCutter e escolha **um dos instaladores** abaixo com duplo clique:
    *   `install_dependencies.bat`: Instalação **padrão** (Recomendada). Mais rápida e à prova de falhas. Usa IAs como Gemini (Grátis) e GPT-4 pela internet.
    *   `install_dependencies_advanced_LocalLLM.bat`: Instalação **avançada**. Dedicada para quem quer rodar IAs 100% offline no hardware (Llama 3, etc). Exige placa de vídeo boa e as ferramentas *C++ Build Tools*.
    
    *(Ambos usam o gerenciador `uv` para configurar tudo automaticamente).*

2.  **Configurar IA (Opcional)**
    -   **Gemini (Recomendado/Free)**: Adicione sua chave em `api_config.json`.
    -   **Local (GGUF)**: Baixe seus modelos `.gguf` favoritos e coloque na pasta `models/`. O ViralCutter irá detectá-los automaticamente.
    -   **TwelveLabs Pegasus (Nativo de vídeo)**: O Pegasus analisa o **vídeo em si** (imagem + áudio), e não só a transcrição, para detectar os momentos mais virais. Adicione sua chave em `twelvelabs.api_key` no `api_config.json` (ou defina a variável de ambiente `TWELVELABS_API_KEY`) e selecione o backend `5` / `--ai-backend twelvelabs`. Requer a URL do vídeo de origem. Pegue uma API key gratuita em [twelvelabs.io](https://twelvelabs.io) (tier gratuito generoso).

3.  **Rodar**
    -   Duplo clique em `run_webui.bat` para abrir a interface no navegador.
    -   Ou use `python main_improved.py` para a versão CLI.

## Exemplos de Saída

**Clip viral com legendas highlight**  
<video src="https://github.com/user-attachments/assets/7a32edce-fa29-4693-985f-2b12313362f3" controls></video>

**Comparação direta: Opus Clip vs ViralCutter** (mesmo vídeo de entrada)  
<video src="https://github.com/user-attachments/assets/12916792-dc0e-4f63-a76b-5698946f50f4" controls></video>

**Modo Split Screen (2 faces)**  
<video src="https://github.com/user-attachments/assets/f5ce5168-04a2-4c9b-9408-949a5400d020" controls></video>

## Roadmap (TODO)

- [x] Lançamento do código
- [ ] Demo permanente no Hugging Face Spaces
- [x] Suporte a 2 pessoas (Split Screen)
- [x] Legendas personalizadas e renderização (Burn)
- [x] Otimização de performance (Código mais rápido)
- [x] Modelos de IA 100% locais (Ollama/Llama/GGUF)
- [x] Tradução automática de legendas
- [x] Rastreamento dinâmico de rosto (O corte segue o movimento)
- [x] Exportação de XML para Premiere Pro (Beta)
- [ ] Música de fundo automática (Auto-Duck)
- [ ] Upload direto para TikTok/YouTube/Instagram
- [ ] Mais formatos de enquadramento (além de 9:16)
- [ ] Watermark opcional

---

## Contribua!

O ViralCutter é mantido pela comunidade. Junte-se a nós para democratizar a criação de conteúdo com IA!
-   **Discord**: [AI Hub Brasil](https://discord.gg/aihubbrasil)
-   **Github**: Dê uma ⭐ estrela se este projeto te ajudou!

**Versão Atual**: 0.8v Alpha
*ViralCutter: Porque clips virais não precisam custar uma fortuna.* 🚀
