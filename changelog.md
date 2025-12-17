# Changelog

## Editor de Legenda JSON

### Funcionalidades
- **Editor de Legendas**: Adicionado um editor de legendas simples, dentro das limitações do Gradio, para corrigir erros de ortografia ocorridos durante o uso do WhisperX.

### Correções
- **Geral**: Alguns Fix Colab e melhorias na geração de viral segments.

## Gradio WebUI & UV Installation

### Nova Interface Web (Gradio)
- **OpusClip Inspired**: Nova interface gráfica construída com Gradio, inspirada no design do OpusClip, oferecendo uma experiência de usuário moderna e intuitiva.
- **Funcionalidades da UI**: Ajustes completos para garantir que todas as funcionalidades da ferramenta estejam acessíveis e operantes através da nova interface.

### Instalação e Infraestrutura
- **Instalação via UV**: Criação de script `.bat` para instalação otimizada de dependências utilizando o `uv`, acelerando o processo de setup.
- **Fixes Gerais**: Correções em diversos componentes que estavam quebrados ou instáveis, garantindo maior estabilidade na execução via UI.

## WebUI 2.0 & Enhanced Configuration

### WebUI Overhaul
- **Dark & Modern UI**: Interface completamente redesenhada com tema escuro e layout em grid responsivo (estilo Opus.pro) para a galeria de vídeos.
- **Dynamic Configuration**: Componentes da interface agora reagem dinamicamente à escolha do Backend de IA, atualizando automaticamente a lista de modelos disponíveis e o tamanho sugerido de chunk.
- **Improved Controls**: Controle granular sobre `Face Detect Interval`, `Skip Prompts`, e `Chunk Size` diretamente na interface web.
- **Refactoring**: Código da WebUI refatorado e modularizado (`library.py` separado do `app.py`) para melhor manutenção.

### Core & CLI
- **Arguments Expansion**: `main_improved.py` agora aceita argumentos de linha de comando para `--chunk-size` e `--ai-model-name`, permitindo override total da configuração.
- **Script Update**: `create_viral_segments.py` atualizado para respeitar os parâmetros passados via CLI, priorizando-os sobre o arquivo de configuração.

## Fix 2 faces

### Melhorias na Detecção Facial e Layout
- **Consistência Visual (2 Faces)**: Implementada lógica para "travar" a identidade dos rostos nas posições superior e inferior, impedindo que os participantes troquem de lugar durante o vídeo.
- **Lógica de Fallback Inteligente**: Caso o rosto não seja detectado no frame atual, o sistema agora tenta recuperar a posição baseada no frame anterior, posterior ou na última coordenada válida conhecida.
- **Intervalo de Detecção Personalizável**: Adicionada configuração para o usuário escolher a frequência da varredura facial, permitindo otimizar o tempo de renderização.

### Correções de Legendas
- **Correção de Sobreposição**: Resolvido bug onde legendas apareciam sobrepostas em momentos de fala rápida.
- **Refinamento de Centralização (2 Faces)**: Ajustes adicionais no cálculo de posição para garantir que a legenda fique perfeitamente centralizada no modo dividido.

## Atualizações Anteriores

### Refatoração e Melhorias de Código
- **Refatoração do Script Principal**: Criação e aprimoramento do `main_improved.py` para melhorar a estrutura e manutenibilidade do pipeline de processamento.
- **Padronização de Código (Inglês)**: Tradução completa de nomes de variáveis, funções e comentários internos para inglês, visando compatibilidade com padrões internacionais e colaboração open-source, mantendo logs de saída com suporte a i18n (`en_US`/`pt_BR`).
- **Ajuste de Diretórios**: Reorganização da estrutura de pastas e caminhos de saída para maior organização dos arquivos gerados.

### Configuração e IA
- **Integração Multi-LLM**: Implementação de suporte ao **g4f** (GPT-4 Free) e **Google Gemini**.
- **API Config**: Centralização das chaves e seleção de modelos no novo arquivo `api_config.json`, permitindo troca rápida de provedor de IA sem alterar o código.
- **Gerenciamento de Prompts**: Criação do arquivo `prompt.txt` para edição fácil do prompt do sistema.

### Legendas e Transcrição (Whisper)
- **Correções no Whisper**: Solução robusta para erros de `unpickling`, conflitos de DLLs (`libprotobuf`, `torchaudio`) e detecção de GPU.
- **Otimização do Fluxo (Slicing)**: O vídeo original é transcrito apenas uma vez. Os cortes reutilizam o JSON original, eliminando a re-transcrição e acelerando o processo.
- **Posicionamento de Legendas**: Correção da lógica de alinhamento para centralização no modo "2-face".

### Processamento de Vídeo e Detecção Facial
- **Novo Motor: InsightFace**: Adição da biblioteca `InsightFace` como motor de detecção facial de alta precisão.
- **MediaPipe**: Manutenção e correção de erros no fallback para o MediaPipe.
- **Limpeza de Logs**: Redução da verbosidade dos logs do FFmpeg no console.