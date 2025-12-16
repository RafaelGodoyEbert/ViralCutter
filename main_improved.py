import os
import sys

# Suppress unnecessary logs before importing heavy libs
os.environ["ORT_LOGGING_LEVEL"] = "3" 
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import warnings
warnings.filterwarnings("ignore")

import json
import shutil
import subprocess
import argparse
import time
from scripts import (
    download_video,
    transcribe_video,
    create_viral_segments,
    cut_segments,
    edit_video,
    transcribe_cuts,
    adjust_subtitles,
    burn_subtitles,
    save_json,
    organize_output,
)
from i18n.i18n import I18nAuto

# Inicializa sistema de tradução
i18n = I18nAuto()
#
# Configurações de Legenda (ASS Style)
# Cores no formato BGR (Blue-Green-Red) para o ASS
COLORS = {
    "red": "0000FF",  # Red
    "yellow": "00FFFF",   # Yellow
    "green": "00FF00",     # Green
    "white": "FFFFFF",    # White
    "black": "000000",     # Black
    "grey": "808080",     # Grey
}

def get_subtitle_config(config_path=None):
    """
    Returns the subtitle configuration dictionary.
    Can be expanded to load from a JSON/YAML file in the future.
    """
    # Default Config
    base_color_transparency = "00"
    outline_transparency = "FF" 
    highlight_color_transparency = "00"
    shadow_color_transparency = "00"
    
    config = {
        "font": "Montserrat-Regular",
        "base_size": 30,
        "base_color": f"&H{base_color_transparency}{COLORS['white']}&",
        "highlight_size": 35,
        "words_per_block": 3,
        "gap_limit": 0.5,
        "mode": 'highlight', # Options: 'no_highlight', 'word_by_word', 'highlight'
        "highlight_color": f"&H{highlight_color_transparency}{COLORS['green']}&",
        "vertical_position": 210, # 1=170(top), ... 4=60(default)
        "alignment": 2, # 2=Center
        "bold": 0,
        "italic": 0,
        "underline": 0,
        "strikeout": 0,
        "border_style": 2, # 1=outline, 3=box
        "outline_thickness": 1.5,
        "outline_color": f"&H{outline_transparency}{COLORS['grey']}&",
        "shadow_size": 2,
        "shadow_color": f"&H{shadow_color_transparency}{COLORS['black']}&",
    }

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
                print(f"Loaded subtitle config from {config_path}")
        except Exception as e:
            print(f"Error loading subtitle config: {e}. Using defaults.")
    
    return config

def interactive_input_int(prompt_text):
    """Solicita um inteiro ao usuário via terminal."""
    while True:
        try:
            value = int(input(i18n(prompt_text)))
            if value > 0:
                return value
            print(i18n("\nError: Number must be greater than 0."))
        except ValueError:
            print(i18n("\nError: The value you entered is not an integer. Please try again."))

def main():
    # Configuração de Argumentos via Linha de Comando (CLI)
    parser = argparse.ArgumentParser(description="ViralCutter CLI")
    parser.add_argument("--url", help="YouTube Video URL")
    parser.add_argument("--segments", type=int, help="Number of segments to create")
    parser.add_argument("--viral", action="store_true", help="Enable viral mode")
    parser.add_argument("--themes", help="Comma-separated themes (if not viral mode)")
    parser.add_argument("--burn-only", action="store_true", help="Skip processing and only burn subtitles")
    parser.add_argument("--min-duration", type=int, default=15, help="Minimum segment duration (seconds)")
    parser.add_argument("--max-duration", type=int, default=90, help="Maximum segment duration (seconds)")
    parser.add_argument("--model", default="large-v3-turbo", help="Whisper model to use")
    
    parser.add_argument("--ai-backend", choices=["manual", "gemini", "g4f"], help="AI backend for viral analysis")
    parser.add_argument("--api-key", help="Gemini API Key (required if ai-backend is gemini)")
    
    parser.add_argument("--chunk-size", help="Override Chunk Size")
    parser.add_argument("--ai-model-name", help="Override AI Model Name")

    parser.add_argument("--project-path", help="Path to existing project folder (overrides URL/Latest)")
    parser.add_argument("--workflow", choices=["1", "2", "3"], default="1", help="Workflow choice: 1=Full, 2=Cut Only, 3=Subtitles Only")
    parser.add_argument("--face-model", choices=["insightface", "mediapipe"], default="insightface", help="Face detection model")
    parser.add_argument("--face-mode", choices=["auto", "1", "2"], default="auto", help="Face tracking mode: auto, 1, 2")
    parser.add_argument("--subtitle-config", help="Path to subtitle configuration JSON file")
    parser.add_argument("--face-detect-interval", type=str, default="0.17,1.0", help="Face detection interval in seconds. Single value or 'interval_1face,interval_2face'")
    parser.add_argument("--skip-prompts", action="store_true", help="Skip interactive prompts and use defaults/existing files")

    args = parser.parse_args()
    
    # Workflow Logic
    workflow_choice = args.workflow
    
    # If Subtitles Only, checking project path
    if workflow_choice == "3" and not args.project_path and not args.url and not args.skip_prompts:
        # Prompt for project path or use latest if not provided?
        pass # Will handle in main flow

    # Modo Apenas Queimar Legenda (Legacy support, mapped to Workflow 3 internally if burn-only is set)
    # Verifica o argumento CLI ou uma variável local hardcoded (para compatibilidade)
    burn_only_mode = args.burn_only

    if burn_only_mode:
        print(i18n("Burn only mode activated. Switching to Workflow 3..."))
        workflow_choice = "3"

    # Obtenção de Inputs (CLI ou Interativo)
    url = args.url
    project_path_arg = args.project_path
    input_video = None

    # Se project_path for fornecido, ignoramos URL
    if project_path_arg:
        if os.path.exists(project_path_arg):
             print(i18n("Using provided project path: {}").format(project_path_arg))
             # Tentar achar o input.mp4 pra manter compatibilidade de variaveis, embora Workflow 3 não precise de download
             possible_input = os.path.join(project_path_arg, "input.mp4")
             if os.path.exists(possible_input):
                 input_video = possible_input
             else:
                 # Se não tiver input.mp4, tudo bem para workflow 3, mas definimos um dummy para não quebrar logica
                 input_video = os.path.join(project_path_arg, "dummy_input.mp4")
             
             # Se for workflow 3, não precisamos de URL
        else:
             print(i18n("Error: Provided project path does not exist."))
             sys.exit(1)

    # Se não temos URL via CLI nem Project Path, pedimos agora
    if not url and not project_path_arg:
        if args.skip_prompts:
             print(i18n("No URL provided and skipping prompts. Trying to load latest project..."))
             # Fallthrough to project loading logic
        else:
            user_input = input(i18n("Enter the YouTube video URL (or press Enter to use latest project): ")).strip()
            if user_input:
                url = user_input
    
    if not url:
        # Usuário apertou Enter (Vazio) -> Tentar pegar último projeto
        base_virals = "VIRALS"
        if os.path.exists(base_virals):
            subdirs = [os.path.join(base_virals, d) for d in os.listdir(base_virals) if os.path.isdir(os.path.join(base_virals, d))]
            if subdirs:
                latest_project = max(subdirs, key=os.path.getmtime)
                detected_video = os.path.join(latest_project, "input.mp4")
                if os.path.exists(detected_video):
                    input_video = detected_video
                    print(i18n("Using latest project: {}").format(latest_project))
                else:
                    print(i18n("Latest project found but 'input.mp4' is missing."))
                    sys.exit(1)
            else:
                print(i18n("No existing projects found in VIRALS folder."))
                sys.exit(1)
        else:
             print(i18n("VIRALS folder not found. Cannot load latest project."))
             sys.exit(1)

    # -------------------------------------------------------------------------
    # Checagem Antecipada de Segmentos Virais (Para pular configurações se já existirem)
    # -------------------------------------------------------------------------
    viral_segments = None
    project_folder_anticipated = None

    if input_video:
        # Se já temos o vídeo, podemos deduzir a pasta
        project_folder_anticipated = os.path.dirname(input_video)
        viral_segments_file = os.path.join(project_folder_anticipated, "viral_segments.txt")
        
        if os.path.exists(viral_segments_file):
             print(i18n("\nExisting viral segments found: {}").format(viral_segments_file))
             if args.skip_prompts:
                 use_existing_json = 'yes'
             else:
                 use_existing_json = input(i18n("Use existing viral segments? (yes/no) [default: yes]: ")).strip().lower()
             
             if use_existing_json in ['', 'y', 'yes']:
                try:
                    with open(viral_segments_file, 'r', encoding='utf-8') as f:
                        viral_segments = json.load(f)
                    print(i18n("Loaded existing viral segments. Skipping configuration prompts."))
                except Exception as e:
                    print(i18n("Error loading JSON: {}.").format(e))

    # Variaveis de config de IA (só necessárias se não tivermos os segmentos)
    num_segments = None
    viral_mode = False
    themes = ""
    ai_backend = "manual" # default
    api_key = None
    
    if not viral_segments:
        num_segments = args.segments
        if not num_segments:
            if args.skip_prompts:
                print("No segments count provided and skip-prompts is ON. Using default 3.")
                num_segments = 3
            else:
                num_segments = interactive_input_int("Enter the number of viral segments to create: ")

        viral_mode = args.viral
        if not args.viral and not args.themes:
            if args.skip_prompts:
                print("Viral mode not set, defaulting to True.")
                viral_mode = True
            else:
                response = input(i18n("Do you want viral mode? (yes/no): ")).lower()
                viral_mode = response in ['yes', 'y']
        
        themes = args.themes if args.themes else ""
        if not viral_mode and not themes:
            if not args.skip_prompts:
                 themes = input(i18n("Enter themes (comma-separated, leave blank if viral mode is True): "))

        # Duration Config
        print(i18n("\nCurrent duration settings: {}s - {}s").format(args.min_duration, args.max_duration))
        if not args.skip_prompts:
            change_dur = input(i18n("Change duration? (y/n) [default: n]: ")).strip().lower()
            if change_dur in ['y', 'yes']:
                 try:
                     min_d = input(i18n("Minimum duration [{}]: ").format(args.min_duration)).strip()
                     if min_d: args.min_duration = int(min_d)
                     
                     max_d = input(i18n("Maximum duration [{}]: ").format(args.max_duration)).strip()
                     if max_d: args.max_duration = int(max_d)
                 except ValueError:
                     print(i18n("Invalid number. Using previous values."))

        # Load API Config
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_config.json')
        api_config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    api_config = json.load(f)
            except:
                pass

        # Seleção do Backend de IA
        ai_backend = args.ai_backend
        
        # Try to load backend from config if not in args
        if not ai_backend and api_config.get("selected_api"):
            ai_backend = api_config.get("selected_api")
            print(i18n("Using AI Backend from config: {}").format(ai_backend))

        if not ai_backend:
            if args.skip_prompts:
                print("No AI backend selected, defaulting to Manual.")
                ai_backend = "manual"
            else:
                print("\n" + i18n("Select AI Backend for Viral Analysis:"))
                print(i18n("1. Gemini API (Best / Recommended)"))
                print(i18n("2. G4F (Free / Experimental)"))
                print(i18n("3. Manual (Copy/Paste Prompt)"))
                choice = input(i18n("Choose (1/2/3): ")).strip()
                
                if choice == "1":
                    ai_backend = "gemini"
                elif choice == "2":
                    ai_backend = "g4f"
                else:
                    ai_backend = "manual"

        api_key = args.api_key
        # Check config for API Key if using Gemini
        if ai_backend == "gemini" and not api_key:
            cfg_key = api_config.get("gemini", {}).get("api_key", "")
            if cfg_key and cfg_key != "SUA_KEY_AQUI":
                api_key = cfg_key
        
        if ai_backend == "gemini" and not api_key:
             if args.skip_prompts:
                 print("Gemini API key missing, but skip-prompts is ON. Might fail.")
             else:
                 print(i18n("Gemini API Key not found in api_config.json or arguments."))
                 api_key = input(i18n("Enter your Gemini API Key: ")).strip()

    # Workflow & Face Config Inputs
    workflow_choice = args.workflow
    face_model = args.face_model
    face_mode = args.face_mode

    # If args weren't provided and we are not skipping prompts, ask user
    # Note: argparse defaults are set, so they "are provided" effectively.
    # To truly detect "not provided", request default=None in argparse. 
    # But for "Simplified Mode", defaults are good.
    # Advanced users use params.
    # We will assume CLI defaults are what we want if skip_prompts is on.
    
    # Logic for detection intervals (Moved out of interactive block to support CLI/WebUI)
    detection_intervals = None
    if args.face_detect_interval:
        try:
            parts = args.face_detect_interval.split(',')
            if len(parts) == 1:
                val = float(parts[0])
                detection_intervals = {'1': val, '2': val}
            elif len(parts) >= 2:
                val1 = float(parts[0])
                val2 = float(parts[1])
                detection_intervals = {'1': val1, '2': val2}
        except ValueError:
            pass

    if not args.burn_only and not args.skip_prompts:
        # Interactive Face Config
        print(i18n("\n--- Face Detection Settings ---"))
        print(i18n("Current Face Model: {} | Mode: {}").format(face_model, face_mode))
        
        if detection_intervals:
             print(i18n("Custom detection intervals: {}").format(detection_intervals))
        else:
             print(i18n("Using dynamic intervals: 1s for 2-face, ~0.16s for 1-face."))


    # Pipeline Execution
    try:
        # 1. Download & Project Setup
        print(f"DEBUG: Checking input_video state. input_video={input_video}")
        
        if not input_video:
            if not url:
                print(i18n("Error: No URL provided and no existing video selected."))
                sys.exit(1)
                
            print(i18n("Starting download..."))
            download_result = download_video.download(url)
            
            if isinstance(download_result, tuple):
                input_video, project_folder = download_result
            else:
                input_video = download_result
                project_folder = os.path.dirname(input_video)
                
            print(f"DEBUG: Download finished. input_video={input_video}, project_folder={project_folder}")
            
        else:
            # Reuso de video existente
            print("DEBUG: Using existing video logic.")
            project_folder = os.path.dirname(input_video)
            
        print(f"Project Folder: {project_folder}")
        
        # 2. Transcribe
        if workflow_choice == "3":
            print(i18n("Workflow 3: Skipping Transcribe."))
            # We assume transcription exists (SRT/JSON) or we won't need it for 'adjust_subtitles' if it uses 'subs/*.json' which are created by 'cut_segments'
            # Actually 'adjust_subtitles' reads from 'project_folder/subs'.
            viral_segments = True # Skip checking
        else:
            print(i18n("Transcribing with model {}...").format(args.model))
            # Se skip config, args.model é default
            srt_file, tsv_file = transcribe_video.transcribe(input_video, args.model, project_folder=project_folder)
 
        # 3. Create Viral Segments
        if workflow_choice != "3":
            # Se não carregamos 'viral_segments' lá em cima (ou se era download novo), checamos agora ou criamos
            if not viral_segments:
                # Checagem tardia para downloads novos que por acaso ja tenham json (Ex: URL repetida)
                viral_segments_file_late = os.path.join(project_folder, "viral_segments.txt")
                if os.path.exists(viral_segments_file_late):
                    print(i18n("Found existing viral segments file at {}").format(viral_segments_file_late))
                    if args.skip_prompts:
                        print(i18n("Skipping prompts enabled. Loading existing segments."))
                        try:
                            with open(viral_segments_file_late, 'r', encoding='utf-8') as f:
                                viral_segments = json.load(f)
                        except Exception as e:
                            print(i18n("Error loading existing JSON: {}. Proceeding to create new segments.").format(e))
                    else:
                        # Ask user if they want to use it
                        pass # (Logic for interactive mode can be added here if needed, but keeping it simple as per request)
                    
                if not viral_segments:
                    print(i18n("Creating viral segments using {}...").format(ai_backend.upper()))
                    viral_segments = create_viral_segments.create(
                        num_segments, 
                        viral_mode, 
                        themes, 
                        args.min_duration, 
                        args.max_duration,
                        ai_mode=ai_backend,
                        api_key=api_key,
                        project_folder=project_folder,
                        chunk_size_arg=args.chunk_size,
                        model_name_arg=args.ai_model_name
                    )
                
                if not viral_segments or not viral_segments.get("segments"):
                    print("Aviso: Nenhum segmento viral foi gerado. Verifique a resposta da IA.")
                
                save_json.save_viral_segments(viral_segments, project_folder=project_folder) 

        # 4. Cut Segments
        # Se workflow for 3, pulamos corte
        if workflow_choice == "3":
            print(i18n("Workflow 3 (Subtitles Only): Skipping Cut and Edit."))
            # Deduzir cuts folder apenas para log
            cuts_folder = os.path.join(project_folder, "cuts")
        else:
            cuts_folder = os.path.join(project_folder, "cuts")
            skip_cutting = False
            
            if os.path.exists(cuts_folder) and os.listdir(cuts_folder):
                print(i18n("\nExisting cuts found in: {}").format(cuts_folder))
                if args.skip_prompts:
                    cut_again_resp = 'no'
                else:
                    cut_again_resp = input(i18n("Cuts already exist. Cut again? (yes/no) [default: no]: ")).strip().lower()
                
                # Default is no (skip) if they just press enter or say no
                if cut_again_resp not in ['y', 'yes']:
                    skip_cutting = True
            
            if skip_cutting:
                print(i18n("Skipping Video Rendering (using existing cuts), but updating Subtitle JSONs..."))
            else:
                print(i18n("Cutting segments..."))

            cut_segments.cut(viral_segments, project_folder=project_folder, skip_video=skip_cutting)
        
        # 5. Workflow Check
        if workflow_choice == "2":
            print(i18n("Cut Only selected. Skipping Face Crop and Subtitles."))
            print(i18n(f"Process completed! Check your results in: {project_folder}"))
            sys.exit(0)

        # 5. Edit Video (Face Crop)
        if workflow_choice != "3":
            print(i18n("Editing video with {} (Mode: {})...").format(face_model, face_mode))
            edit_video.edit(project_folder=project_folder, face_model=face_model, face_mode=face_mode, detection_period=detection_intervals)
        else:
            print(i18n("Workflow 3: Skipping Face Crop."))

        # 6. Subtitles
        burn_subtitles_option = True 
        if burn_subtitles_option:
            print(i18n("Processing subtitles..."))
            # transcribe_cuts removido: JSON de legenda já é gerado no corte
            # transcribe_cuts.transcribe(project_folder=project_folder)
            
            sub_config = get_subtitle_config(args.subtitle_config)
            

            
            # Passa o dicionário desempacotado como argumentos, mais o project_folder
            adjust_subtitles.adjust(project_folder=project_folder, **sub_config)
            
            burn_subtitles.burn(project_folder=project_folder)
        else:
            print(i18n("Subtitle burning skipped."))

        # Organização Final (Opcional, pois agora já está tudo em project_folder)
        # organize_output.organize(project_folder=project_folder)
        
        print(i18n("Process completed! Check your results in: {}").format(project_folder))

    except Exception as e:
        print(i18n("\nAn error occurred: {}").format(str(e)))
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
