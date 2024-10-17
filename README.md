# ViralCutter: Gerador de Vídeos Virais
[ ![](https://dcbadge.vercel.app/api/server/aihubbrasil) ](https://discord.gg/aihubbrasil) <br>
[English](https://github.com/RafaelGodoyEbert/ViralCutter/blob/main/README_en.md) | [Português](https://github.com/RafaelGodoyEbert/ViralCutter/blob/main/README.md)

## **Descrição**
ViralCutter é uma ferramenta inovadora para gerar vídeos virais a partir de conteúdo existente. Com técnicas avançadas de processamento de vídeo e áudio, o ViralCutter corta e edita segmentos de vídeo que são perfeitos para compartilhamento em redes sociais. Utilizando o modelo WhisperX para transcrição e geração de legendas automáticas, ele adapta os vídeos para o formato 9:16 (vertical), ideal para plataformas como TikTok e Instagram com Reels e Youtube com Shorts.

## **Funcionalidades**

- **Download de Vídeos**: Baixa vídeos do YouTube através de uma URL fornecida.
- **Transcrição de Áudio**: Converte áudio em texto utilizando o modelo WhisperX.
- **Identificação de Segmentos Virais**: Utiliza IA para detectar partes do vídeo com alto potencial de viralização.
- **Corte e Ajuste de Formato**: Corta os segmentos selecionados e ajusta a proporção para 9:16.
- **Mesclagem de Áudio e Vídeo**: Combina o áudio transcrito com os clipes de vídeo processados.
- **Exportação em Lote**: Gera um arquivo ZIP com todos os vídeos virais criados, facilitando o download e compartilhamento.
- **Legenda personalizada**: Você cria uma legenda personalizada com cores, highlight, sem highlight ou palavra por palavra, tendo uma ampla possibilidade de edição.

## **Como Usar**
<!-- 
Entre no link e siga os passos na ordem:<br> [![Open In Colab](https://img.shields.io/badge/Colab-F9AB00?style=for-the-badge&logo=googlecolab&color=525252)](https://colab.research.google.com/drive/1gcxImzBt0ObWLfW3ThEcwqKhasB4WpgX?usp=sharing)
HF [![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)]()
-->
- Entre no link e siga os passos na ordem: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1UZKzeqjIeEyvq9nPx7s_4mU6xlkZQn_R?usp=sharing#scrollTo=pa36OeArowme) <br>
- Versão simplificada sem opção de mudança de texto [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1aDNLtoJZa9Z0lKcYTR6CGNMgZ_iTpwJD?usp=sharing) <br>
- Criei esse site para ajudar a dividir a trascrição, já que ChatGPT tem limites: [Split text for ChatGPT](https://rafaelgodoyebert.github.io/ViralCutter/)

## **Limitações**

- O tempo de processamento pode ser elevado para vídeos longos.
- A qualidade dos vídeos gerados pode variar com base na qualidade do vídeo original.

## Inspiração:
Este projeto foi inspirado nos seguintes repositórios:

*   [Reels Clips Automator](https://github.com/eddieoz/reels-clips-automator)
*   [YoutubeVideoToAIPoweredShorts](https://github.com/Fitsbit/YoutubeVideoToAIPoweredShorts)

## TODO📝
- [x] Release code
- [ ] Huggingface SpaceDemo
- [x] Two face in the cut
- [x] Custom caption and burn
- [x] Make the code faster
- [ ] More types of framing beyond 9:16
- [x] The cut follows the face as it moves
- [ ] Automatic translation
- [ ] Satisfactory video on the side
- [ ] Background music
- [ ] watermark at user's choice
- [ ] Upload directly to YouTube channel

## Exemplos
### Exmplo de vídeo viral ``com highlight ativo`` [comprimido pra caber no github]
https://github.com/user-attachments/assets/dd9a7039-e0f3-427a-a6e1-f50ab5029082

### Exemplo Opus Clip vs ViralCutter [comprimido pra caber no github]
https://github.com/user-attachments/assets/12916792-dc0e-4f63-a76b-5698946f50f4

### Exemplo 2 faces [comprimido pra caber no github]
https://github.com/user-attachments/assets/ca7ebb9c-52ba-4171-a513-625bef690a2b

## **Contribuições**
Quer ajudar a tornar o ViralCutter ainda melhor? Se você tiver sugestões ou quiser contribuir com o código, fique à vontade para abrir uma issue ou enviar um pull request no nosso repositório do GitHub.

## **Versão**
`0.6v Alpha`  
Uma alternativa gratuita ao `opus.pro` e ao `vidyo.ai`.

---
