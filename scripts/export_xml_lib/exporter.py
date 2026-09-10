import os
import json
import shutil
import zipfile
from .utils import json_to_srt, get_video_dims
from .face_detection import detect_faces_jit
from .rendering import render_segmented_overlays
from .xml_generator import create_premiere_xml

def export_pack(project_path, segment_index, output_format="premiere", subtitle_config_path=None):
    """
    Generates a ZIP Pack for the segment.
    subtitle_config_path: Optional path to a JSON file with user's subtitle style config.
    """
    print(f"Iniciando Pacote de Exportação para o Projeto: {os.path.basename(project_path)}, Segmento: {segment_index}")
    
    # Paths
    proj_name = os.path.basename(project_path)
    cut_dir = os.path.join(project_path, "cuts")
    
    # 1. IDENTIFY VIDEO FILE
    video_file = None
    original_scale_file = None
    
    if os.path.exists(cut_dir):
        files = os.listdir(cut_dir)
        # Search for {index}_..._original_scale.mp4 or similar
        prefix_idx = f"{segment_index:03d}_"
        
        for f in files:
            if f.startswith(prefix_idx) and (f.endswith(".mp4") or f.endswith(".mov")):
                 video_file = os.path.join(cut_dir, f)
                 break
    
    if not video_file:
        print(f"Erro: Nenhum arquivo de vídeo encontrado para o segmento {segment_index} em {cut_dir}")
        return
        
    print(f"Vídeo Selecionado: {video_file}")

    # 2. IDENTIFY SUBTITLE FILES
    subs_dir = os.path.join(project_path, "subs_ass")
    ass_file = None
    
    if os.path.exists(subs_dir):
        sub_files = os.listdir(subs_dir)
        prefix_idx = f"{segment_index:03d}_"
        # Prioritize Clean Processed > Processed > Any
        patterns = [
            (lambda f: f.endswith(".ass") and f.startswith(prefix_idx) and "processed" in f and "original" not in f), 
            (lambda f: f.endswith(".ass") and f.startswith(prefix_idx) and "processed" in f), 
            (lambda f: f.endswith(".ass") and f.startswith(prefix_idx))
        ]
        for p in patterns:
            if ass_file: break
            for f in sub_files:
                if p(f):
                    ass_file = os.path.join(subs_dir, f)
                    break
    
    # JSON in 'subs' usually
    subs_json_dir = os.path.join(project_path, "subs")
    json_file = None
    if os.path.exists(subs_json_dir):
        sub_files = os.listdir(subs_json_dir)
        prefix_idx = f"{segment_index:03d}_"
        # Same pattern priority
        json_patterns = [
            (lambda f: f.endswith(".json") and f.startswith(prefix_idx) and "processed" in f),
            (lambda f: f.endswith(".json") and f.startswith(prefix_idx))
        ]
        for p in json_patterns:
            if json_file: break
            for f in sub_files:
                if p(f):
                    json_file = os.path.join(subs_json_dir, f)
                    break

    # 2.1 IDENTIFY FACE COORDS
    final_dir = os.path.join(project_path, "final")
    face_data = None
    if os.path.exists(final_dir):
        final_files = os.listdir(final_dir)
        prefix_idx = f"{segment_index:03d}_"
        for f in final_files:
            if f.startswith(prefix_idx) and f.endswith("_coords.json"):
                try:
                    with open(os.path.join(final_dir, f), 'r') as fd:
                        face_data = json.load(fd)
                        print(f"Coordenadas Faciais Encontradas: {f}")
                except Exception as e:
                    print(f"Erro ao carregar coordenadas faciais: {e}")
                break
    
    if face_data is None:
        print("Nenhum dado facial pré-computado encontrado. Tentando detecção JIT...")
        try:
            face_data = detect_faces_jit(video_file)
        except Exception as e:
            print(f"Erro na detecção JIT: {e}")

    # 3. PREPARE STAGING
    export_name = f"export_{proj_name}_seg{segment_index}"
    stage_dir = os.path.join(project_path, export_name)
    
    # Ensure directory exists (overwrite files inside instead of nuke directory to avoid locking issues)
    os.makedirs(stage_dir, exist_ok=True)
    
    # 4. COPY VIDEO (Prefer Original Scale for XML editing)
    source_video_to_copy = video_file
    dest_filename = "video_cut.mp4"
    
    # Try to find original scale version in 'cuts' folder
    try:
        cuts_dir = os.path.dirname(video_file)
        # Attempt 1: Direct suffix replacement
        original_scale_candidate = video_file.replace(".mp4", "_original_scale.mp4")
        
        if not os.path.exists(original_scale_candidate):
             # Attempt 2: Search by prefix
             prefix_idx = f"{segment_index:03d}_"
             if os.path.exists(cuts_dir):
                 for f in os.listdir(cuts_dir):
                     if f.startswith(prefix_idx) and "original_scale" in f and f.endswith(".mp4"):
                         original_scale_candidate = os.path.join(cuts_dir, f)
                         break
        
        if os.path.exists(original_scale_candidate):
            print(f"Usando Fonte em Escala Original para Exportação: {original_scale_candidate}")
            source_video_to_copy = original_scale_candidate
            dest_filename = "video_source.mp4" # Distinct name
    except Exception as e:
        print(f"Erro ao verificar vídeo original scale: {e}")
    
    dest_video = os.path.join(stage_dir, dest_filename)
    
    # Tratamento de Arquivo Bloqueado (Premiere)
    try:
        shutil.copy2(source_video_to_copy, dest_video)
    except PermissionError:
        print(f"AVISO: O arquivo {dest_filename} está bloqueado (provavelmente aberto no Premiere).")
        import time
        timestamp = int(time.time())
        dest_filename = dest_filename.replace(".mp4", f"_{timestamp}.mp4")
        dest_video = os.path.join(stage_dir, dest_filename)
        print(f"Salvando com novo nome para evitar conflito: {dest_filename}")
        shutil.copy2(source_video_to_copy, dest_video)
    
    # 5. SUBTITLES & SEGMENTS (No Rendering - XML Only)
    overlay_segments = []
    jdata_segs = []
    
    # Load JSON if available
    if json_file:
         try:
             with open(json_file, 'r', encoding='utf-8') as f:
                 jdata = json.load(f)
             if isinstance(jdata, dict) and "segments" in jdata:
                 jdata_segs = jdata["segments"]
             elif isinstance(jdata, list):
                 jdata_segs = jdata
         except Exception as e:
             print(f"Erro ao carregar JSON: {e}")
             
    if jdata_segs:
        print(f"Processados {len(jdata_segs)} segmentos de legenda para XML.")
        # Build dummy overlay segments to drive the cutter logic
        for idx, s in enumerate(jdata_segs):
            overlay_segments.append({
                'start': s.get('start', 0),
                'end': s.get('end', 0),
                'text': s.get('text', ''),
                'highlights': s.get('highlights', []),
                'path': None, # No video file
                'index': idx
            })
    else:
        print("Nenhum segmento de legenda encontrado. XML será cortado continuamente.")

    # 6. GENERATE SRT (Standard)
    dest_srt = os.path.join(stage_dir, f"{proj_name}_Seg{segment_index}.srt")
    if json_file:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                jdata_srt = json.load(f)
            if isinstance(jdata_srt, dict) and "segments" in jdata_srt:
                jdata_srt = jdata_srt["segments"]
            srt_content = json_to_srt(jdata_srt)
            with open(dest_srt, 'w', encoding='utf-8') as f:
                f.write(srt_content)
        except Exception: pass

    # 7. LOAD USER SUBTITLE CONFIG (if available)
    subtitle_config = None
    
    # Priority 1: process_config.json in project root (most reliable source)
    process_config_path = os.path.join(project_path, "process_config.json")
    if os.path.exists(process_config_path):
        try:
            with open(process_config_path, 'r', encoding='utf-8') as f:
                process_config = json.load(f)
            raw_config = process_config.get('subtitle_config', {})
            if raw_config:
                subtitle_config = _convert_app_config_to_xml_config(raw_config)
                print(f"Configuração de legenda carregada de: {process_config_path}")
        except Exception as e:
            print(f"Erro ao carregar process_config.json: {e}")
    
    # Priority 2: Explicit path or temp file
    if not subtitle_config:
        config_paths_to_try = []
        if subtitle_config_path:
            config_paths_to_try.append(subtitle_config_path)
        config_paths_to_try.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_subtitle_config.json"))
        
        for cfg_path in config_paths_to_try:
            if cfg_path and os.path.exists(cfg_path):
                try:
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        raw_config = json.load(f)
                    # These files have the config directly (not nested)
                    subtitle_config = _convert_app_config_to_xml_config(raw_config)
                    print(f"Configuração de legenda carregada de: {cfg_path}")
                    break
                except Exception as e:
                    print(f"Erro ao carregar configuração de legenda de {cfg_path}: {e}")
    
    if subtitle_config:
        print(f"  Fonte: {subtitle_config.get('font')}, Tamanho: {subtitle_config.get('font_size')}")
        print(f"  Cor Texto: {subtitle_config.get('text_color')}, Destaque: {subtitle_config.get('highlight_color')}")
        print(f"  Modo: {subtitle_config.get('mode')}, Negrito: {subtitle_config.get('bold')}")
    else:
        print("Nenhuma configuração de legenda encontrada. Usando padrões (Arial, branco, destaque amarelo).")

    # 8. LOAD FACE MODES (For Subtitle Positioning)
    face_mode = "1"
    face_modes_path = os.path.join(project_path, "face_modes.json")
    if os.path.exists(face_modes_path):
        try:
            with open(face_modes_path, 'r') as f:
                all_modes = json.load(f)
            # Try to match key by segment index
            # export_name is "export_Project_seg0"
            # Keys in JSON are likely "output000" or similar from edit_video.py
            # Let's try to construct key or search
            search_key = f"output{segment_index:03d}"
            if search_key in all_modes:
                face_mode = all_modes[search_key]
                print(f"Modo de Face Detectado para Segmento {segment_index}: {face_mode}")
        except Exception as e:
            print(f"Erro ao carregar modos de face: {e}")

    # 8. GENERATE XML
    width_src, height_src, duration, fps = get_video_dims(dest_video)
    
    # Validation for resolution mismatch
    if face_data:
        max_x = 0
        for entry in face_data:
            for f in entry.get('faces', []):
                if len(f) >= 3 and f[2] > max_x: max_x = f[2]
        if max_x > width_src:
            print(f"Correção: Detectando fonte 4K com base nas coordenadas faciais ({max_x} > {width_src})")
            width_src = 3840
            height_src = 2160
    
    print(f"DEBUG: Passando dados faciais para XML: {len(face_data) if face_data else 'Nenhum'}")
    
    # Logic to Determine Sequence Resolution
    seq_w = 1080
    seq_h = 1920
    
    if width_src > 3000 or height_src > 3000:
        print("Conteúdo 4K Detectado. Configurando Sequência para 4K Vertical (2160x3840).")
        seq_w = 2160
        seq_h = 3840
    else:
        print("Fonte é 1080p ou menor. Configurando Sequência para 1080p Vertical (1080x1920).")

    xml_content = create_premiere_xml(
        project_name=proj_name, 
        video_path=dest_video,
        overlay_segments=overlay_segments,
        duration_frames=duration,
        width=seq_w, 
        height=seq_h,
        timebase=int(fps),
        scale_value=100.0,
        face_data=face_data,
        source_width=width_src,
        source_height=height_src,
        subtitle_data=jdata_segs,
        subtitle_config=subtitle_config,
        face_mode=face_mode
    )
    
    xml_output = os.path.join(stage_dir, "timeline.xml")
    with open(xml_output, "w", encoding="utf-8") as f:
        f.write(xml_content)
        
    print("XML Customizado para Premiere Gerado (Segmentos Estilo Opus).")

    # 9. ZIP IT
    zip_path = f"{stage_dir}.zip"
    shutil.make_archive(stage_dir, 'zip', stage_dir)
    
    print(f"SUCESSO: Pacote de Exportação criado em {zip_path}")
    
    # Cleanup
    try:
        # shutil.rmtree(stage_dir)
        pass
    except: pass
    
    return zip_path


def _ass_color_to_hex(ass_color):
    """
    Convert ASS color format (&HAABBGGRR or &HBBGGRR) to standard hex (#RRGGBB).
    ASS uses BGR order. If the color is already #hex format, return as-is.
    """
    if not ass_color:
        return None
    
    # Already hex format
    if ass_color.startswith('#'):
        return ass_color
    
    # Strip &H prefix and & suffix
    color = ass_color.replace('&H', '').replace('&h', '').replace('&', '').strip()
    
    # Pad to 6 or 8 characters
    color = color.zfill(6)
    
    if len(color) == 8:
        # Format: AABBGGRR
        bb = color[2:4]
        gg = color[4:6]
        rr = color[6:8]
    elif len(color) == 6:
        # Format: BBGGRR
        bb = color[0:2]
        gg = color[2:4]
        rr = color[4:6]
    else:
        return '#FFFFFF'  # Fallback
    
    return f"#{rr}{gg}{bb}"


def _convert_app_config_to_xml_config(raw_config):
    """
    Convert the subtitle config from app.py format (ASS colors, base_size, etc.)
    to the format expected by xml_generator.py (hex colors, font_size, etc.)
    """
    xml_config = {}
    
    # Font
    xml_config['font'] = raw_config.get('font', 'Arial')
    xml_config['font_size'] = raw_config.get('base_size', 84)
    xml_config['highlight_size'] = raw_config.get('highlight_size', int(xml_config['font_size'] * 1.2))
    
    # Colors (convert from ASS BGR to hex RGB)
    xml_config['text_color'] = _ass_color_to_hex(raw_config.get('base_color', '#FFFFFF'))
    xml_config['highlight_color'] = _ass_color_to_hex(raw_config.get('highlight_color', '#FFFF00'))
    xml_config['stroke_color'] = _ass_color_to_hex(raw_config.get('outline_color', '#000000'))
    xml_config['shadow_color'] = _ass_color_to_hex(raw_config.get('shadow_color', '#000000'))
    
    # Stroke/Shadow
    xml_config['stroke_width'] = raw_config.get('outline_thickness', 2)
    xml_config['shadow_offset'] = raw_config.get('shadow_size', 2) * 2
    xml_config['shadow_opacity'] = 100
    
    # Visibility
    xml_config['stroke_visible'] = raw_config.get('outline_thickness', 0) > 0
    xml_config['shadow_visible'] = raw_config.get('shadow_size', 0) > 0
    xml_config['fill_over_stroke'] = True
    
    # Style flags
    xml_config['bold'] = bool(raw_config.get('bold', 0))
    xml_config['italic'] = bool(raw_config.get('italic', 0))
    xml_config['all_caps'] = bool(raw_config.get('uppercase', 0))
    xml_config['underline'] = bool(raw_config.get('underline', 0))
    
    # Background (border_style 3 = opaque box)
    border_style = raw_config.get('border_style', 1)
    xml_config['back_visible'] = (border_style == 3 or border_style == "3")
    xml_config['back_color'] = _ass_color_to_hex(raw_config.get('outline_color', '#000000'))  # ASS uses outline color for box
    xml_config['back_opacity'] = 75
    xml_config['back_size'] = 0
    xml_config['back_radius'] = 10
    
    # Alignment (ASS: 1=Left, 2=Center, 3=Right → Premiere: 0=Left, 2=Center, 1=Right)
    ass_align = raw_config.get('alignment', 2)
    align_map = {1: 0, 2: 2, 3: 1}  # ASS to Premiere
    xml_config['alignment'] = align_map.get(ass_align, 2)
    
    # Position (vertical_position from ASS MarginV)
    # Convert pixel position to normalized 0-1 range
    vert_pos = raw_config.get('vertical_position', 200)
    # In a 1920px tall sequence, MarginV=200 means ~200px from bottom
    # Premiere uses 0=top, 1=bottom. So: pos_y = 1 - (marginV / height)
    # For 1920: pos_y = 1 - (200/1920) ≈ 0.896
    xml_config['pos_x_norm'] = 0.5
    xml_config['pos_y_norm'] = 1.0 - (vert_pos / 1920.0) if vert_pos < 1920 else 0.8
    
    # Mode and words_per_block for highlight generation
    xml_config['mode'] = raw_config.get('mode', 'highlight')
    xml_config['words_per_block'] = raw_config.get('words_per_block', 3)
    
    # Text transformations
    xml_config['remove_punctuation'] = raw_config.get('remove_punctuation', False)
    
    return xml_config

