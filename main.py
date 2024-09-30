import os
from scripts import download_video, transcribe_video, create_viral_segments, cut_segments, edit_video, transcribe_cuts, adjust_subtitles, burn_subtitles, save_json

# Create necessary directories
os.makedirs('tmp', exist_ok=True)
os.makedirs('final', exist_ok=True)
os.makedirs('subs', exist_ok=True)
os.makedirs('subs_ass', exist_ok=True)
os.makedirs('burned_sub', exist_ok=True)

# Cores originais invertidas
vermelho = "0A08E4"
amarelo = "00FFFF" 
azul = "700206"
preto = "000000" 
verde = "58DA7D" 
branco = "FFFFFF"
laranja = "0099FE" 
roxo = "800080"
rosa = "C77DF9"
ciano = "FFFF00" 
marrom = "2D4A8C"
cinza = "808080" 
verde_limao = "32CD32" 
azul_claro = "E6D8AD" 
verde = "0FF00"

# Subtitle variables
fonte = "Arial" #Arial, Times New Roman #No colab acho que todas do Google Fonts, no Windows/Linux as instaladas no seu sistema
base_size = 12 #12
base_color_t = "00" # 00= totalmente opaco, 80=  50% transparente, FF= Totalmente transparente
base_color = f"&H{base_color_t}" + "FFFFFF" + "&" #FFFFFF (branco) ou 00FFFF (amarelo)
contorno_t = "FF" # 00= totalmente opaco, 80=  50% transparente, FF= Totalmente transparente
contorno = f"&H{contorno_t}" + "808080" + "&" #808080
h_size = 14 #14 (Default)
palavras_por_bloco = 3 #5 (Default)
limite_gap = 0.5 #0.5 (Default)
modo = 'highlight' #sem_higlight, palavra_por_palavra, highlight
highlight_color_t = "00" # 00= totalmente opaco, 80=  50% transparente, FF= Totalmente transparente
highlight_color = f"&H{highlight_color_t}" + "0FF00" + "&" #0FF00
posicao_vertical = 60 # Divide de 1 à 5 contando um no topo. 1=170, 2=130, 3=99, 4=60 (default), 5=20
cor_da_sombra_t = "00" # 00= totalmente opaco, 80=  50% transparente, FF= Totalmente transparente
cor_da_sombra = f"&H{cor_da_sombra_t}" + "000000" + "&" #000000
alinhamento = 2 #1= Esquerda, 2= Centro (default), 3= Direita
negrito = 0 #(1 para ativar, 0 para desativar)
italico = 0 #(1 para ativar, 0 para desativar)
sublinhado = 0 #(1 para ativar, 0 para desativar)
tachado = 0 #(1 para ativar, 0 para desativar)
estilo_da_borda = 3 #(1 para contorno, 3 para caixa).
espessura_do_contorno = 1.5 #1.5 (Default)
tamanho_da_sombra = 10 #10 (Default)

# Burn subtitles option
burn_only = False
burn_subtitles_option = True

# Transcript variables
model = 'large-v3'

if burn_only:
    print("Burn only mode activated. Skipping to subtitle burning...")
    burn_subtitles.burn()
    print("Subtitle burning completed.")
else:
    # Input variables
    url = input("Enter the YouTube video URL: ")
    num_segments = int(input("Enter the number of viral segments to create: "))
    viral_mode = input("Do you want viral mode? (yes/no): ").lower() == 'yes'
    themes = input("Enter themes (comma-separated, leave blank if viral mode is True): ") if not viral_mode else ''
    
    tempo_minimo = 15 #int(input("Enter the minimum duration for segments (in seconds): "))
    tempo_maximo = 90 #int(input("Enter the maximum duration for segments (in seconds): "))

    # Execute the pipeline
    input_video = download_video.download(url)
    srt_file, tsv_file = transcribe_video.transcribe(input_video, model)

    viral_segments = create_viral_segments.create(num_segments, viral_mode, themes, tempo_minimo, tempo_maximo)
    save_json.save_viral_segments(viral_segments)

    cut_segments.cut(viral_segments)
    edit_video.edit()

    if burn_subtitles_option:
        transcribe_cuts.transcribe()
        adjust_subtitles.adjust(base_color, base_size, h_size, highlight_color, palavras_por_bloco, limite_gap, modo, posicao_vertical, alinhamento, fonte, contorno, cor_da_sombra, negrito, italico, sublinhado, tachado, estilo_da_borda, espessura_do_contorno, tamanho_da_sombra)
        burn_subtitles.burn()
    else:
        print("Subtitle burning skipped.")

    print("Process completed successfully!")