# ViralCutter - Fork com Notebooks Kaggle e Colab

Fork do [ViralCutter](https://github.com/RafaelGodoyEbert/ViralCutter) com notebooks otimizados para Kaggle e Google Colab.

## 📚 O que é o ViralCutter?

Uma alternativa gratuita ao `opus.pro` e ao `vidyo.ai` para criar cortes automáticos de vídeos longos (podcasts, lives, etc.) em clipes virais para Reels/Shorts/TikTok usando IA.

## 🚀 Notebooks Disponíveis

### 🔵 Google Colab
**Características:**
- ✅ Instalação rápida (3-5 min)
- ✅ Upload automático para Google Drive
- ✅ Otimizado para GPUs T4
- ❌ Zoom inteligente removido (mais leve)

**Como usar:**
1. Abra o notebook no Colab (link em breve)
2. Execute a célula principal
3. Aguarde a instalação
4. Clique no link `gradio.live` gerado
5. Processe seus vídeos - os cortes irão automaticamente para seu Drive!

### 🟠 Kaggle
**Características:**
- ✅ 30h/semana de GPU grátis
- ✅ Upload OAuth para sua conta Drive
- ✅ Suporte a datasets persistentes
- ✅ Documentação completa de configuração

**Como usar:**
1. **Configure os datasets primeiro** (veja seção abaixo)
2. Abra o notebook no Kaggle (link em breve)
3. Execute a célula principal
4. Faça a autenticação OAuth quando solicitado
5. Clique no link `gradio.live` gerado

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

Segue a mesma licença do projeto original.
