# 🎬 ViralCutter - Smooth Face Tracking Edition

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/masterface77/ViralCutter/blob/smooth-zoom/ViralCutter-SmoothZoom.ipynb)
[![Open in Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)](https://www.kaggle.com/code/levireis77/viralcutter-kaggle-smoothzoom)
[![Discord](https://dcbadge.limes.pink/api/server/tAdPHFAbud)](https://discord.gg/tAdPHFAbud)

> **🎯 Branch `smooth-zoom`** - Versão com **YOLO Smooth Tracking** + face tracking configurável!

Fork do [ViralCutter](https://github.com/RafaelGodoyEbert/ViralCutter) com **Smooth Face Tracking** - a câmera segue o rosto de forma suave e cinematográfica.

---

## ✨ Novidades v0.9 - Smooth Face Tracking

![Smooth Tracking](https://img.shields.io/badge/🎥-Smooth_Tracking-blueviolet?style=for-the-badge)

### 🎥 Tracking Suave Configurável
A suavidade do tracking agora pode ser ajustada no Gradio!

| Alpha | Efeito |
|-------|--------|
| 0.02 | Ultra Suave (câmera bem lenta) |
| 0.05 | Normal (padrão recomendado) |
| 0.10 | Rápido (acompanha mais de perto) |

### ⚙️ Configuração via Interface
- **"Advanced Face Settings"** no Gradio
- **Slider "Tracking Smoothness"** para ajustar alpha
- Aplica-se apenas ao modo YOLO

**Tecnologias:**
- 🔍 **YOLOv8** - Detecção e tracking de pessoas em tempo real
- 📊 **ByteTrack** - IDs persistentes para cada pessoa
- 📈 **EMA (Exponential Moving Average)** - Suavização configurável

### ⚡ Otimização T4 (WhisperX)
Transcrição otimizada para GPUs T4 do Colab/Kaggle (16GB VRAM):

| Configuração | Valor | Benefício |
|--------------|-------|-----------|
| `compute_type` | int8_float16 | 50% menos VRAM |
| `model` | large-v2 | Mais estável que v3 |
| `batch_size` | 8 | Evita OOM em vídeos longos |
| `language` | pt (padrão) | Pula detecção automática |
| `chunk_size` | 15 | Chunks maiores = mais eficiente |

---

## 🚀 Notebooks Disponíveis

### 🔵 Colab - Smooth Zoom
**Características:**
- ✅ YOLO Smooth Zoom **ATIVADO POR PADRÃO**
- ✅ Upload automático para Google Drive
- ✅ Otimizado para GPUs T4
- ✅ Instalação rápida (3-5 min)

**Como usar:**
1. Abra o notebook [ViralCutter-SmoothZoom.ipynb](https://colab.research.google.com/github/masterface77/ViralCutter/blob/smooth-zoom/ViralCutter-SmoothZoom.ipynb)
2. Execute a célula principal
3. Aguarde a instalação (inclui `ultralytics`)
4. Clique no link `gradio.live` gerado
5. Face Model já vem selecionado como **yolo** 🎯

### 🟠 Kaggle - Smooth Zoom  
**Características:**
- ✅ 30h/semana de GPU grátis
- ✅ Upload OAuth para sua conta Drive
- ✅ YOLO Smooth Zoom incluído
- ✅ Suporte a cookies e datasets

---

## 📦 Configurando Datasets no Kaggle

O notebook do Kaggle requer algumas credenciais. Siga o guia completo:

### 1️⃣ client_secret.json (Obrigatório)
Credenciais OAuth do Google Cloud para upload no Drive.

**Passos:**
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto ou use um existente
3. Vá em **APIs & Services** → **Credentials**
4. **Create Credentials** → **OAuth 2.0 Client ID**
5. Escolha **Desktop App**
6. Baixe o JSON
7. No Kaggle: **Add Data** → **Upload** → Faça upload
8. Nomeie o dataset como `client-secret-json`

### 2️⃣ cookie (Opcional)
Cookies para download de vídeos privados/restritos.

**Passos:**
1. Instale [Get cookies.txt LOCAL](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. Acesse www.kaggle.com (logado)
3. Clique na extensão → **Export**
4. Salve como `www.youtube.com_cookies.txt`
5. No Kaggle: **Add Data** → **Upload**
6. Nomeie o dataset como `cookie`

### 3️⃣ credenciais-google (Obrigatório)
API Key do Gemini para análise com IA.

**Passos:**
1. Acesse [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Create API Key**
3. Copie a chave
4. Crie arquivo `gemini_api.txt` com a chave
5. No Kaggle: **Add Data** → **Upload**
6. Nomeie o dataset como `credenciais-google`

### 4️⃣ google-drive-credentials (Opcional)
Token OAuth reutilizável (gerado na primeira execução).

**Como reutilizar:**
1. Execute o notebook uma vez
2. Após autenticação, baixe o arquivo `.json` gerado em `/kaggle/working/`
3. Crie dataset no Kaggle com este arquivo
4. Nomeie como `google-drive-credentials`

---

## ✨ Diferenças entre Colab e Kaggle

| Característica | Colab | Kaggle |
|----------------|-------|--------|
| GPU Grátis | ✅ 12h/dia | ✅ 30h/semana |
| Configuração | Mais simples | Requer datasets |
| Upload Drive | Nativo   | OAuth manual |
| Zoom IA | ❌ Removido | ✅ Disponível |
| Persistência | ❌ Nenhuma | ✅ Datasets |

---

## 🎯 Recursos

- **Detecção automática** de momentos virais
- **Transcrição com IA** (WhisperX)
- **Corte inteligente** com análise semântica
- **Legendas automáticas**
- **Processamento em batch**

---

## 🔗 Links Úteis

- **Licença (GPL v3):** [LICENSE](LICENSE)
- **Repositório Original:** [RafaelGodoyEbert/ViralCutter](https://github.com/RafaelGodoyEbert/ViralCutter)
- **Discord (Suporte):** [discord.gg/tAdPHFAbud](https://discord.gg/tAdPHFAbud)

---

## 📝 Créditos

Desenvolvido por **Rafa.Godoy**
- [GitHub](https://github.com/rafaelGodoyEbert)
- [Twitter](https://twitter.com/GodoyEbert)
- [Instagram](https://www.instagram.com/rafael.godoy.ebert/)

Fork customizado para facilitar uso em Kaggle e Colab.

---

## 📄 Licença

Este projeto é licenciado sob a **GNU General Public License v3**, permitindo que você copie, distribua e modifique o software livremente, desde que mantenha a mesma licença. [Leia a licença completa aqui](LICENSE).

<a id="viralcutter-original"></a>
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

### Pré-requisitos
- Python 3.10+
- FFmpeg instalado no sistema
- **GPU NVIDIA** (Altamente recomendada para velocidade e funcionalidades de IA local)

### Passo a Passo

1.  **Instale as dependências**
    Execute o script `install_dependencies.bat`. Ele usa o gerenciador `uv` para configurar tudo em segundos.

2.  **Configurar IA (Opcional)**
    -   **Gemini (Recomendado/Free)**: Adicione sua chave em `api_config.json`.
    -   **Local (GGUF)**: Baixe seus modelos `.gguf` favoritos e coloque na pasta `models/`. O ViralCutter irá detectá-los automaticamente.

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
