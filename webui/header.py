import os
import sys

# Necessary if this file is imported from app.py which is in the same dir but we need root for i18n
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(WORKING_DIR)

from i18n.i18n import I18nAuto
i18n = I18nAuto()

badges = """
<div style="display: flex; align-items: center; justify-content: center;">
<span style="margin-right: 5px;"> 

[ ![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white) ](https://github.com/rafaelGodoyEbert)
 
</span>
<span style="margin-right: 5px;"> 

[ ![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white) ](https://twitter.com/GodoyEbert)
 
</span>
<span style="margin-right: 5px;"> 

[ ![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white) ](https://www.instagram.com/rafael.godoy.ebert)
 
</span>

<!-- ÍCONE DO COLAB ADICIONADO AQUI -->
<span style="margin-right: 5px;">

[ ![Open In Colab](https://img.shields.io/badge/Open%20in%20Colab-%23F9AB00.svg?style=for-the-badge&logo=googlecolab&logoColor=white) ]("https://colab.research.google.com/drive/1UZKzeqjIeEyvq9nPx7s_4mU6xlkZQn_R")

</span>
<!-- FIM DA ADIÇÃO -->

<span>

[![](https://dcbadge.limes.pink/api/server/tAdPHFAbud)](https://discord.gg/tAdPHFAbud)

</span>
</div>
"""

description = f"""
<div style="text-align: center;">

<h1>ViralCutter</h1>
<p style="font-size: 1.1em; margin-bottom: 20px;">{i18n('Bem-vindo ao ViralCutter! A ferramenta definitiva para transformar vídeos longos em clipes virais com o poder da IA.')}</p>

<div style="display: inline-block; text-align: left; background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
<p style="margin-bottom: 10px;"><strong>{i18n('Aqui você pode:')}</strong></p>
<ul style="margin: 0; padding-left: 20px;">
<li>✂️ <strong>{i18n('Cortes Automáticos')}</strong>: {i18n('Identifique e corte os melhores momentos baseado em viralidade.')}</li>
<li>📝 <strong>{i18n('Legendas Dinâmicas')}</strong>: {i18n('Crie legendas estéticas (Estilo Hormozi) automaticamente.')}</li>
<li>🤖 <strong>{i18n('IA Avançada')}</strong>: {i18n('Suporte integrado para')} <strong>Gemini</strong> e <strong>G4F</strong>.</li>
<li>📱 <strong>{i18n('Foco em Vertical')}</strong>: {i18n('Detecção facial inteligente para vídeos verticais (TikTok/Shorts/Reels).')}</li>
</ul>
</div>

<br>
<div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
    <a href='https://www.youtube.com/@aihubbrasil' target='_blank'>
        <img src="https://img.shields.io/badge/AI_HUB_Brasil-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="Youtube do AI HUB Brasil">
    </a>
    <a href='https://www.youtube.com/@godoyy' target='_blank'>
        <img src="https://img.shields.io/badge/Canal_Pessoal_Godoyy-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="Canal Pessoal Godoyy">
    </a>
</div>
<br>{i18n('Este projeto foi desenvolvido para a comunidade do AI HUB Brasil.')}
</div>
"""