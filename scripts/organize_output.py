import os
import json
import shutil
import re
from i18n.i18n import I18nAuto

i18n = I18nAuto()

def sanitize_filename(name):
    """Remove caracteres inválidos para nomes de arquivos/pastas."""
    # Remove caracteres inválidos como / \ : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    # Remove espaços extras e quebras de linha
    cleaned = cleaned.strip()
    return cleaned

def organize():
    print(i18n("Organizing output files..."))
    
    # Caminhos
    meta_path = "tmp/viral_segments.txt"
    burned_folder = "burned_sub"
    virals_root = "VIRALS"
    
    if not os.path.exists(meta_path):
        print(i18n("Metadata file not found: ") + meta_path)
        return
        
    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            segments = data.get("segments", [])
    except Exception as e:
        print(i18n("Error reading metadata: ") + str(e))
        return

    os.makedirs(virals_root, exist_ok=True)
    
    processed_count = 0
    
    for i, segment in enumerate(segments):
        title = segment.get("title", f"Viral_Segment_{i+1}")
        clean_title = sanitize_filename(title)
        
        # Se o título estiver vazio após sanitização, usa fallback
        if not clean_title:
            clean_title = f"Viral_Segment_{i+1}"
            
        # Cria pasta do viral
        viral_folder = os.path.join(virals_root, clean_title)
        os.makedirs(viral_folder, exist_ok=True)
        
        # Identifica o arquivo de vídeo final
        # Padrão esperado: outputXXX_original_scale_subtitled.mp4
        # O padrão pode variar dependendo de como o burn_subtitles foi executado, mas geralmente segue o index
        # Vamos tentar localizar pelo padrão de índice
        
        video_filename_pattern = f"output{str(i).zfill(3)}_original_scale_subtitled.mp4"
        source_video = os.path.join(burned_folder, video_filename_pattern)
        
        # Se não encontrar com subtitled, tenta sem (caso burn tenha sido pulado?)
        if not os.path.exists(source_video):
            # Tenta na pasta 'final' se não tiver legenda queimada
            source_video_final = os.path.join("final", f"output{str(i).zfill(3)}_original_scale.mp4")
            if os.path.exists(source_video_final):
                source_video = source_video_final
            else:
                # Tenta padrao sem 'original_scale' ou outras variações se necessário
                print(i18n(f"Warning: Could not find video file for segment {i+1} ({title})"))
                continue
                
        # Define caminhos finais
        target_video = os.path.join(viral_folder, f"{clean_title}.mp4")
        target_json = os.path.join(viral_folder, f"{clean_title}.json")
        
        # Mover/Copiar Vídeo
        try:
            shutil.copy2(source_video, target_video)
        except Exception as e:
            print(i18n(f"Error copying video for segment {i}: {e}"))
            continue
            
        # Salvar JSON individual
        try:
            with open(target_json, 'w', encoding='utf-8') as f:
                json.dump(segment, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(i18n(f"Error saving JSON for segment {i}: {e}"))
            
        processed_count += 1
        print(i18n(f"Saved: {clean_title}"))

    print(i18n(f"Organization completed. {processed_count} virals saved in '{virals_root}' folder."))

if __name__ == "__main__":
    organize()
