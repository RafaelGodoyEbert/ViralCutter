import gradio as gr
import subprocess
import os
import sys
import json
import psutil
import shutil
import datetime
import time
import urllib.parse
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn


import re
import library # Module for Library Logic
import subtitle_handler as subs # Module for Subtitles
import subtitle_editor as editor # Module for Editor Logic

# Path to the main script
MAIN_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main_improved.py")
WORKING_DIR = os.path.dirname(MAIN_SCRIPT_PATH)
sys.path.append(WORKING_DIR)

from i18n.i18n import I18nAuto
i18n = I18nAuto()

# --- PRESETS DEFINITIONS ---
FACE_PRESETS = {
    "Default (Balanced)": {"thresh": 0.35, "two_face": 0.60, "conf": 0.40, "dead_zone": 150},
    "Stable (Focus Main)": {"thresh": 0.60, "two_face": 0.80, "conf": 0.60, "dead_zone": 200},
    "Sensitive (Catch All)": {"thresh": 0.10, "two_face": 0.40, "conf": 0.30, "dead_zone": 100},
    "High Precision": {"thresh": 0.40, "two_face": 0.65, "conf": 0.75, "dead_zone": 150},
}

EXPERIMENTAL_PRESETS = {
    "Default (Off)": {"focus": False, "mar": 0.03, "score": 1.5, "motion": False, "motion_th": 3.0, "motion_sens": 0.05, "decay": 2.0},
    "Active Speaker (Balanced)": {"focus": True, "mar": 0.03, "score": 1.5, "motion": True, "motion_th": 3.0, "motion_sens": 0.05, "decay": 2.0},
    "Active Speaker (Sensitive)": {"focus": True, "mar": 0.02, "score": 1.0, "motion": True, "motion_th": 2.0, "motion_sens": 0.10, "decay": 1.0},
    "Active Speaker (Stable)": {"focus": True, "mar": 0.05, "score": 2.5, "motion": False, "motion_th": 5.0, "motion_sens": 0.02, "decay": 3.0},
}
# ---------------------------

VIRALS_DIR = os.path.join(WORKING_DIR, "VIRALS")
MODELS_DIR = os.path.join(WORKING_DIR, "models")

# Ensure directories exist
if not os.path.exists(VIRALS_DIR):
    os.makedirs(VIRALS_DIR, exist_ok=True)
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR, exist_ok=True)

# Global variables
current_process = None

# Helpers
def convert_color_to_ass(hex_color, alpha="00"):
    try:
        with open("debug_colors.log", "a") as f:
             f.write(f"INPUT: '{hex_color}'\n")
    except: pass

    if not hex_color:
        return f"&H{alpha}FFFFFF&"
    
    hex_clean = hex_color.lstrip('#').strip()
    
    # Handle rgb/rgba format: rgb(255, 215, 0)
    if hex_clean.lower().startswith("rgb"):
        try:
            # Extract numbers including floats
            nums = re.findall(r"[\d\.]+", hex_clean)
            if len(nums) >= 3:
                r = int(float(nums[0]))
                g = int(float(nums[1]))
                b = int(float(nums[2]))
                # Clamp
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                # Convert to hex
                ret = f"&H{alpha}{b:02X}{g:02X}{r:02X}&".upper()
                try:
                    with open("debug_colors.log", "a") as f:
                         f.write(f"PARSED RGB: {ret}\n")
                except: pass
                return ret
        except Exception as e:
            try:
                with open("debug_colors.log", "a") as f:
                     f.write(f"RGB ERROR: {e}\n")
            except: pass

    # Handle 3-digit hex (e.g. F00 -> FF0000)
    if len(hex_clean) == 3:
        hex_clean = "".join([c*2 for c in hex_clean])
        
    if len(hex_clean) == 6:
        r = hex_clean[0:2]
        g = hex_clean[2:4]
        b = hex_clean[4:6]
        # Uppercase just in case
        ret = f"&H{alpha}{b}{g}{r}&".upper() 
        try:
            with open("debug_colors.log", "a") as f:
                 f.write(f"PARSED HEX: {ret}\n")
        except: pass
        return ret
        
    try:
        with open("debug_colors.log", "a") as f:
             f.write(f"INVALID: Defaulting to White\n")
    except: pass
    return f"&H{alpha}FFFFFF&"

def kill_process():
    global current_process
    if current_process:
        try:
            parent = psutil.Process(current_process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            current_process = None
            return i18n("Process terminated.")
        except Exception as e:
            return i18n("Error terminating process: {}").format(e)
    return i18n("No process running.")

GEMINI_MODELS = [
    'gemini-3-pro-preview',
    'gemini-2.5-flash',
    'gemini-2.5-flash-preview-09-2025',
    'gemini-2.5-flash-lite',
    'gemini-2.5-flash-lite-preview-09-2025',
    'gemini-2.5-pro',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite'
]

G4F_MODELS = [
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4',
    'o1-mini',
    'o1',
    'deepseek-r1',
    'deepseek-v3',
    'llama-3.3-70b',
    'llama-3.1-405b',
    'claude-3.5-sonnet',
    'claude-3.7-sonnet',
    'gemini-2.0-flash',
    'qwen-2.5-72b'
]

def get_local_models():
    if not os.path.exists(MODELS_DIR): return []
    return [f for f in os.listdir(MODELS_DIR) if f.endswith(".gguf")]



def apply_face_preset(preset_name):
    if preset_name not in FACE_PRESETS:
        return [gr.update() for _ in range(4)] # No change
    
    p = FACE_PRESETS[preset_name]
    return p["thresh"], p["two_face"], p["conf"], p["dead_zone"]

def apply_experimental_preset(preset_name):
    if preset_name not in EXPERIMENTAL_PRESETS:
        return [gr.update() for _ in range(7)] # No change
        
    p = EXPERIMENTAL_PRESETS[preset_name]
    return p["focus"], p["mar"], p["score"], p["motion"], p["motion_th"], p["motion_sens"], p["decay"]

# Subtitle logic moved to subtitle_handler.py


def run_viral_cutter(input_source, project_name, url, video_file, segments, viral, themes, min_duration, max_duration, model, ai_backend, api_key, ai_model_name, chunk_size, workflow, face_model, face_mode, face_detect_interval, no_face_mode, 
                     tracking_alpha, face_filter_thresh, face_two_thresh, face_conf_thresh, face_dead_zone, focus_active_speaker, active_speaker_mar, active_speaker_score_diff, include_motion, active_speaker_motion_threshold, active_speaker_motion_sensitivity, active_speaker_decay,
                     use_custom_subs, font_name, font_size, font_color, highlight_color, outline_color, outline_thickness, shadow_color, shadow_size, is_bold, is_italic, is_uppercase, vertical_pos, alignment,
                     h_size, w_block, gap, mode, under, strike, border_s, remove_punc, video_quality, use_youtube_subs, translate_target):
    
    global current_process
    yield "", gr.update(value=i18n("Running..."), interactive=False), gr.update(visible=True), None 

    cmd = [sys.executable, MAIN_SCRIPT_PATH]
    
    # Input Source Logic
    if input_source == "Existing Project":
        if not project_name:
             yield i18n("Error: No project selected."), gr.update(value=i18n("Start Processing"), interactive=True), gr.update(visible=False), None
             return
        full_project_path = os.path.join(VIRALS_DIR, project_name)
        cmd.extend(["--project-path", full_project_path])
    elif input_source == "Upload Video":
        if not video_file:
             yield i18n("Error: No video file uploaded."), gr.update(value=i18n("Start Processing"), interactive=True), gr.update(visible=False), None
             return
        
        # Determine project name from filename
        original_filename = os.path.basename(video_file)
        name_no_ext = os.path.splitext(original_filename)[0]
        # Sanitize: Allow alphanumeric, space, dash, underscore
        safe_name = "".join([c for c in name_no_ext if c.isalnum() or c in " _-"]).strip()
        if not safe_name: safe_name = "Untitled_Upload"
        
        # Always append timestamp as requested
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name_upload = f"{safe_name}_{timestamp}"
        project_path = os.path.join(VIRALS_DIR, project_name_upload)
             
        os.makedirs(project_path, exist_ok=True)
        
        target_path = os.path.join(project_path, "input.mp4")
        shutil.copy(video_file, target_path)
        
        cmd.extend(["--project-path", project_path])
        # Skip YouTube subs as it is a local upload
        cmd.append("--skip-youtube-subs")
        
    else:
        if url: cmd.extend(["--url", url])
        # Pass Video Quality
        if video_quality: cmd.extend(["--video-quality", video_quality])
        # Pass Subtitle Option (if False, we skip)
        if not use_youtube_subs: cmd.append("--skip-youtube-subs")
        
    # Translation
    if translate_target and translate_target != "None":
            cmd.extend(["--translate-target", translate_target])

    
    cmd.extend(["--segments", str(int(segments))])
    if viral: cmd.append("--viral")
    if themes: cmd.extend(["--themes", themes])
    cmd.extend(["--min-duration", str(int(min_duration))])
    cmd.extend(["--max-duration", str(int(max_duration))])
    cmd.extend(["--model", model])
    cmd.extend(["--ai-backend", ai_backend])
    if api_key: cmd.extend(["--api-key", api_key])
    
    # New AI Params
    if ai_model_name: cmd.extend(["--ai-model-name", str(ai_model_name)])
    if chunk_size: cmd.extend(["--chunk-size", str(int(chunk_size))])

    workflow_map = {"Full": "1", "Cut Only": "2", "Subtitles Only": "3"}
    cmd.extend(["--workflow", workflow_map.get(workflow, "1")])
    print(f"[DEBUG] Using face_model: {face_model}")
    cmd.extend(["--face-model", face_model])
    cmd.extend(["--face-mode", face_mode])
    if face_detect_interval: cmd.extend(["--face-detect-interval", str(face_detect_interval)])
    if no_face_mode: cmd.extend(["--no-face-mode", no_face_mode])
    
    # New Face Params
    if face_filter_thresh is not None: cmd.extend(["--face-filter-threshold", str(face_filter_thresh)])
    if face_two_thresh is not None: cmd.extend(["--face-two-threshold", str(face_two_thresh)])
    if face_conf_thresh is not None: cmd.extend(["--face-confidence-threshold", str(face_conf_thresh)])
    if face_dead_zone is not None: cmd.extend(["--face-dead-zone", str(face_dead_zone)])
    if tracking_alpha is not None: cmd.extend(["--tracking-alpha", str(tracking_alpha)])


    
    cmd.append("--skip-prompts")
    
    if focus_active_speaker:
        cmd.append("--focus-active-speaker")
        if active_speaker_mar is not None: cmd.extend(["--active-speaker-mar", str(active_speaker_mar)])
        if active_speaker_score_diff is not None: cmd.extend(["--active-speaker-score-diff", str(active_speaker_score_diff)])
        if include_motion: cmd.append("--include-motion")
        if active_speaker_motion_threshold is not None: cmd.extend(["--active-speaker-motion-threshold", str(active_speaker_motion_threshold)])
        if active_speaker_motion_sensitivity is not None: cmd.extend(["--active-speaker-motion-sensitivity", str(active_speaker_motion_sensitivity)])
        if active_speaker_decay is not None: cmd.extend(["--active-speaker-decay", str(active_speaker_decay)])

    cmd.append("--skip-prompts") # Always skip prompts in WebUI to prevent freezing

    if use_custom_subs:
        subtitle_config = {
            "font": font_name, "base_size": int(font_size), "base_color": convert_color_to_ass(font_color), "highlight_color": convert_color_to_ass(highlight_color),
            "outline_color": convert_color_to_ass(outline_color), "outline_thickness": outline_thickness, "shadow_color": convert_color_to_ass(shadow_color),
            "shadow_size": shadow_size, "vertical_position": vertical_pos, "alignment": alignment, "bold": 1 if is_bold else 0, "italic": 1 if is_italic else 0, 
            "underline": 1 if under else 0, "strikeout": 1 if strike else 0, "border_style": border_s, "words_per_block": int(w_block), "gap_limit": gap,
            "mode": mode, "highlight_size": int(h_size), "remove_punctuation": remove_punc
        }
        # Uppercase is handled in main script or logic? 
        # Actually subtitle_config doesn't seem to natively support "uppercase" in get_subtitle_config default, but app.py was using it. 
        # I should probably add it back if I want to support it, but user said "PROHIBITED to remove existing ones".
        # I'll re-add 'uppercase': 1 if is_uppercase else 0 to the dict if the backend supports it, otherwise it's just ignored.
        # But wait, main_improved.py doesn't have 'uppercase' in get_subtitle_config. 
        # I'll keep it in the dict just in case logic uses it elsewhere or if I missed it.
        # Actually, standard ASS doesn't support uppercase flag directly in Style, it needs to be text transform.
        # But I'll leave it in the dict.
        subtitle_config["uppercase"] = 1 if is_uppercase else 0

        subtitle_config_path = os.path.join(WORKING_DIR, "temp_subtitle_config.json")
        try:
            with open(subtitle_config_path, "w", encoding="utf-8") as f:
                json.dump(subtitle_config, f, indent=4)
            cmd.extend(["--subtitle-config", subtitle_config_path])
        except Exception: pass 
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    try:
        current_process = subprocess.Popen(cmd, cwd=WORKING_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, env=env)
        logs = ""
        project_folder_path = None
        if input_source == "Existing Project" and project_name:
             # If using existing project, we already know the path, but let's see if logs confirm it
             project_folder_path = os.path.join(VIRALS_DIR, project_name)

        last_update_time = time.time()
        
        while True:
            line = current_process.stdout.readline()
            if not line and current_process.poll() is not None:
                break
            
            if line:
                logs += line
                if "Project Folder:" in line:
                    parts = line.split("Project Folder:")
                    if len(parts) > 1: project_folder_path = parts[1].strip()
                
                # Throttle updates to avoid browser freeze (0.2s interval)
                current_time = time.time()
                if current_time - last_update_time > 0.2:
                    yield logs, gr.update(visible=True, interactive=False), gr.update(visible=True), None
                    last_update_time = current_time
        
        # Final yield to ensure all logs are shown
        yield logs, gr.update(visible=True, interactive=False), gr.update(visible=True), None
    except Exception as e:
        logs += f"\nError running process: {str(e)}\n"
        yield logs, gr.update(visible=True, interactive=False), gr.update(visible=True), None
    finally:
        if current_process:
            if current_process.stdout:
                try:
                    current_process.stdout.close()
                except Exception: pass
            if current_process.poll() is None:
                # If we are here, it means we finished reading or errored out, but process is still running.
                # If it was a normal break from loop, process should be done or close to done.
                # If we are stopping, current_process.terminate() might be needed outside? 
                # But here we just wait.
                try:
                    current_process.wait()
                except Exception: pass
            current_process = None
    
    # Wait to ensure filesystem flush
    time.sleep(1.0)
    
    html_output = ""
    if project_folder_path and os.path.exists(project_folder_path):
        html_output = library.generate_project_gallery(project_folder_path, is_full_path=True)
    else:
        html_output = f"<h3>{i18n('Error: Project folder could not be determined from logs.')}</h3>"
    yield logs, gr.update(value=i18n("Start Processing"), interactive=True), gr.update(visible=False), html_output

css = """
/* Global Dark Theme Overrides */
body, .gradio-container {
    background-color: #0b0b0b !important;
    color: #ffffff !important;
}

/* Force dark background for specific inputs that might be white */
input[type="password"], textarea, select {
    background-color: #1f1f1f !important;
    color: #ffffff !important;
    border: 1px solid #333 !important;
}

/* Hide Footer */
footer {visibility: hidden}

/* Container Width */
.gradio-container {
    max-width: 98% !important; 
    width: 98% !important;
    margin: 0 auto !important;
}
"""

import header

with gr.Blocks(title=i18n("ViralCutter WebUI"), theme=gr.themes.Default(primary_hue="orange", neutral_hue="slate"), css=css) as demo:
    gr.Markdown(header.badges)
    gr.Markdown(header.description)
    with gr.Tabs():
        with gr.Tab(i18n("Create New")):
             with gr.Row():
                with gr.Column(scale=1):
                    input_source = gr.Radio([(i18n("YouTube URL"), "YouTube URL"), (i18n("Existing Project"), "Existing Project"), (i18n("Upload Video"), "Upload Video")], label=i18n("Input Source"), value="YouTube URL")
                    
                    url_input = gr.Textbox(label=i18n("YouTube URL"), placeholder="https://www.youtube.com/watch?v=...", visible=True)
                    video_upload = gr.File(label=i18n("Upload Video"), file_count="single", file_types=["video"], visible=False)
                    
                    with gr.Row():
                        video_quality_input = gr.Dropdown(choices=["best", "4k", "1440p", "1080p", "720p", "480p"], label=i18n("Video Quality"), value="4k")
                        translate_input = gr.Dropdown(choices=["None", "pt", "en", "es", "fr", "de", "it", "ru", "ja", "ko", "zh-CN"], label=i18n("Translate Subtitles To"), value="None")
                        use_youtube_subs_input = gr.Checkbox(label=i18n("Use YouTube Subs"), value=True, info=i18n("Download and use official subtitles if available. (Recommended, it speeds up the process)"))

                    project_selector = gr.Dropdown(choices=[], label=i18n("Select Project"), visible=False)
                    
                    def on_source_change(source):
                        if source == "YouTube URL":
                            return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(value="Full") 
                        elif source == "Upload Video":
                             return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(value="Full")
                        else:
                            # Load projects
                            projs = library.get_existing_projects()
                            return gr.update(visible=False), gr.update(choices=projs, visible=True), gr.update(visible=False), gr.update(value="Subtitles Only")
                    
                    
                    with gr.Row():
                        segments_input = gr.Number(label=i18n("Segments"), value=3, precision=0)
                        viral_input = gr.Checkbox(label=i18n("Viral Mode"), value=True)
                    themes_input = gr.Textbox(label=i18n("Themes"), placeholder=i18n("funny, sad..."), visible=False)
                    viral_input.change(lambda x: gr.update(visible=not x), viral_input, themes_input)
                    with gr.Row():
                        min_dur_input = gr.Number(label=i18n("Min Duration (s)"), value=15)
                        max_dur_input = gr.Number(label=i18n("Max Duration (s)"), value=90)
                with gr.Column(scale=1):
                    with gr.Row():
                        ai_backend_input = gr.Dropdown(choices=[(i18n("Gemini"), "gemini"), (i18n("G4F"), "g4f"), (i18n("Local (GGUF)"), "local"), (i18n("Manual"), "manual")], label=i18n("AI Backend"), value="gemini", scale=2)
                        api_key_input = gr.Textbox(label=i18n("Gemini API Key"), type="password", scale=3)
                    
                    # New Dynamic Inputs
                    with gr.Row():
                        ai_model_input = gr.Dropdown(choices=GEMINI_MODELS, label=i18n("AI Model"), value=GEMINI_MODELS[1], allow_custom_value=True, visible=True, scale=5)
                        refresh_models_btn = gr.Button("🔄", size="sm", visible=False, scale=0, min_width=50) # Only local
                        chunk_size_input = gr.Number(label=i18n("Chunk Size"), value=70000, precision=0, scale=2)
                    
                    # Update listeners with logic to hide/show API key
                    def update_ai_ui(backend):
                        show_api = (backend == "gemini")
                        show_refresh = (backend == "local")
                        
                        # Definições padrão para evitar que fiquem vazios
                        new_choices = []
                        new_val = ""
                        new_chunk = 70000
                        
                        if backend == "gemini":
                            new_choices = GEMINI_MODELS
                            new_val = GEMINI_MODELS[1]
                            new_chunk = 70000
                        elif backend == "g4f":
                            new_choices = G4F_MODELS
                            new_val = G4F_MODELS[5]
                            new_chunk = 70000
                        elif backend == "local":
                            models = get_local_models()
                            new_choices = models if models else [i18n("No models found")]
                            new_val = new_choices[0]
                            new_chunk = 30000
                        else: # Manual
                             pass

                        return (
                            gr.update(visible=show_api), # API Key Visibility (Fixes hole 1)
                            gr.update(choices=new_choices, value=new_val, visible=(backend != "manual")), # Model Dropdown
                            gr.update(visible=show_refresh), # Refresh Button
                            gr.update(value=new_chunk) # Chunk Size
                        )

                    def refresh_local_models():
                        models = get_local_models()
                        val = models[0] if models else i18n("No models found")
                        return gr.update(choices=models, value=val)

                    refresh_models_btn.click(refresh_local_models, outputs=ai_model_input)
                    ai_backend_input.change(update_ai_ui, inputs=ai_backend_input, outputs=[api_key_input, ai_model_input, refresh_models_btn, chunk_size_input])

                    model_input = gr.Dropdown(["tiny", "small", "medium", "large", "large-v1", "large-v2", "large-v3", "turbo", "large-v3-turbo", "distil-large-v2", "distil-medium.en", "distil-small.en", "distil-large-v3"], label=i18n("Whisper Model"), value="large-v3-turbo")
                    with gr.Row():
                        workflow_input = gr.Dropdown(choices=[(i18n("Full"), "Full"), (i18n("Cut Only"), "Cut Only"), (i18n("Subtitles Only"), "Subtitles Only")], label=i18n("Workflow"), value="Full")
                        face_model_input = gr.Dropdown(["yolo", "insightface", "mediapipe"], label=i18n("Face Model"), value="yolo", info="YOLO = Smooth Zoom")
                    with gr.Row():
                        face_mode_input = gr.Dropdown(choices=[(i18n("Auto"), "auto"), ("1", "1"), ("2", "2")], label=i18n("Face Mode"), value="auto")
                        face_detect_interval_input = gr.Textbox(label=i18n("Face Det. Interval"), value="0.17,1.0")
                        no_face_mode_input = gr.Dropdown(choices=[(i18n("Padding (9:16)"), "padding"), (i18n("Zoom (Center)"), "zoom"), (i18n("Blur Background"), "blur")], label=i18n("No Face Fallback"), value="zoom")
                    
                    
                    # Update listeners now that all components are defined
                    input_source.change(on_source_change, inputs=input_source, outputs=[url_input, project_selector, video_upload, workflow_input])
             
             with gr.Accordion(i18n("Advanced Face Settings"), open=False):
                 # Tracking Smoothness Slider (YOLO only)
                 gr.Markdown(f"### {i18n('Camera Tracking')}")
                 tracking_alpha_input = gr.Slider(
                     label=i18n("Tracking Smoothness"), 
                     minimum=0.01, maximum=0.15, value=0.05, step=0.01,
                     info=i18n("0.02 = Ultra Suave (lento) | 0.05 = Normal | 0.10 = Rápido")
                 )
                 
                 gr.Markdown(f"### {i18n('Face Detection')}")
                 face_preset_input = gr.Dropdown(choices=[(i18n(k), k) for k in FACE_PRESETS.keys()], label=i18n("Configuration Presets"), value="Default (Balanced)", interactive=True)
                 with gr.Row():
                      face_filter_thresh_input = gr.Slider(label=i18n("Ignore Small Faces (0.0 - 1.0)"), minimum=0.0, maximum=1.0, value=0.35, step=0.05, info=i18n("Relative size to ignore background."))
                      face_two_thresh_input = gr.Slider(label=i18n("Threshold for 2 Faces (0.0 - 1.0)"), minimum=0.0, maximum=1.0, value=0.60, step=0.05, info=i18n("Size of 2nd face to activate split mode."))
                      face_conf_thresh_input = gr.Slider(label=i18n("Minimum Confidence (0.0 - 1.0)"), minimum=0.0, maximum=1.0, value=0.40, step=0.05, info=i18n("Ignore detections with low confidence."))
                      face_dead_zone_input = gr.Slider(label=i18n("Dead Zone (Stabilization)"), minimum=0, maximum=200, value=150, step=5, info=i18n("Movement pixels to ignore."))
                 
                 face_preset_input.change(apply_face_preset, inputs=face_preset_input, outputs=[face_filter_thresh_input, face_two_thresh_input, face_conf_thresh_input, face_dead_zone_input])

                 with gr.Accordion(i18n("Experimental: Active Speaker & Motion"), open=False):
                        experimental_preset_input = gr.Dropdown(choices=[(i18n(k), k) for k in EXPERIMENTAL_PRESETS.keys()], label=i18n("Configuration Presets"), value="Default (Off)", interactive=True)
                        focus_active_speaker_input = gr.Checkbox(label=i18n("Experimental: Focus on Speaker"), value=False, info=i18n("Tries to focus only on the speaking person instead of split screen."))
                        with gr.Row():
                            active_speaker_mar_input = gr.Slider(label=i18n("MAR Threshold (Mouth Open)"), minimum=0.01, maximum=0.20, value=0.03, step=0.005, info=i18n("Mouth open sensitivity."))
                            active_speaker_score_diff_input = gr.Slider(label=i18n("Score Difference"), minimum=0.5, maximum=10.0, value=1.5, step=0.5, info=i18n("Minimum difference to focus on 1 face."))
                            
                        with gr.Row():
                            include_motion_input = gr.Checkbox(label=i18n("Consider Motion"), value=False, info=i18n("Increases score with motion (gestures)."))
                            
                        with gr.Row():
                            active_speaker_motion_threshold_input = gr.Slider(label=i18n("Motion Dead Zone"), minimum=0.0, maximum=20.0, value=3.0, step=0.5, info=i18n("Pixels ignored."))
                            active_speaker_motion_sensitivity_input = gr.Slider(label=i18n("Motion Sensitivity"), minimum=0.01, maximum=0.5, value=0.05, step=0.01, info=i18n("Points per pixel."))
                            active_speaker_decay_input = gr.Slider(label=i18n("Switch Speed"), minimum=0.5, maximum=5.0, value=2.0, step=0.5, info=i18n("Speed to lose focus."))

                        experimental_preset_input.change(apply_experimental_preset, inputs=experimental_preset_input, outputs=[focus_active_speaker_input, active_speaker_mar_input, active_speaker_score_diff_input, include_motion_input, active_speaker_motion_threshold_input, active_speaker_motion_sensitivity_input, active_speaker_decay_input])
             with gr.Accordion(i18n("Subtitle Settings (alpha)"), open=False):
                preset_input = gr.Dropdown(choices=[(i18n("Manual"), "Manual")] + [(i18n(k), k) for k in subs.SUBTITLE_PRESETS.keys()], label=i18n("Quick Presets"), value="Hormozi (Classic)")
                use_custom_subs = gr.Checkbox(label=i18n("Enable Subtitle Customization (Includes Preset)"), value=True)
                
                # Previews (Always Visible)
                preview_html = gr.HTML(value=f"<div style='text-align:center; padding:10px; color:#666;'>{i18n('Select options or preset to preview')}</div>")
                
                with gr.Row():
                    preview_vid_btn = gr.Button(i18n("🎬 Render Animated Preview (Slow)"), size="sm")
                preview_vid = gr.Video(label=i18n("Animated Preview"), height=300, autoplay=True, interactive=False)
                
                with gr.Accordion(i18n("Advanced Settings"), open=False):
                    gr.Markdown(f"### {i18n('Appearance')}")
                    with gr.Row():
                        font_name_input = gr.Textbox(label=i18n("Font Name"), value="Montserrat-Regular")
                        font_size_input = gr.Slider(label=i18n("Font Size (Base)"), minimum=8, maximum=80, value=12)
                        highlight_size_input = gr.Slider(label=i18n("Highlight Size"), minimum=8, maximum=80, value=14)
                    
                    with gr.Row():
                        font_color_input = gr.ColorPicker(label=i18n("Base Color"), value="#FFFFFF")
                        highlight_color_input = gr.ColorPicker(label=i18n("Highlight Color"), value="#00FF00")
                        outline_color_input = gr.ColorPicker(label=i18n("Outline Color"), value="#000000")
                        shadow_color_input = gr.ColorPicker(label=i18n("Shadow Color"), value="#000000")
                    
                    gr.Markdown(f"### {i18n('Styling & Effects')}")
                    with gr.Row():
                        outline_thickness_input = gr.Slider(label=i18n("Outline Thickness"), minimum=0, maximum=10, value=1.5)
                        shadow_size_input = gr.Slider(label=i18n("Shadow Size"), minimum=0, maximum=10, value=2)
                        border_style_input = gr.Dropdown(choices=[(i18n("Outline"), 1), (i18n("Opaque Box"), 3)], label=i18n("Border Style"), value=1)
                    
                    with gr.Row():
                        bold_input = gr.Checkbox(label=i18n("Bold"))
                        italic_input = gr.Checkbox(label=i18n("Italic"))
                        uppercase_input = gr.Checkbox(label=i18n("Uppercase"))
                        remove_punc_input = gr.Checkbox(label=i18n("Remove Punctuation"), value=True)
                        underline_input = gr.Checkbox(label=i18n("Underline"))
                        strikeout_input = gr.Checkbox(label=i18n("Strikeout"))
                        
                    gr.Markdown(f"### {i18n('Positioning & Layout')}")
                    with gr.Row():
                        vertical_pos_input = gr.Slider(label=i18n("V-Pos (Margin V)"), minimum=0, maximum=500, value=210)
                        alignment_input = gr.Dropdown(choices=[(i18n("Left"), 1), (i18n("Center"), 2), (i18n("Right"), 3)], label=i18n("Alignment"), value=2)
                        gap_limit_input = gr.Slider(label=i18n("Gap Limit"), minimum=0.0, maximum=5.0, value=0.5, step=0.1)
                        mode_input = gr.Dropdown(choices=[(i18n("Highlight"), "highlight"), (i18n("Word by Word"), "word_by_word"), (i18n("No Highlight"), "no_highlight")], label=i18n("Mode"), value="highlight")
                        words_per_block_input = gr.Slider(label=i18n("Words per Block"), minimum=1, maximum=20, value=3, step=1)

                manual_inputs = [
                    font_name_input, font_size_input, font_color_input, highlight_color_input, 
                    outline_color_input, outline_thickness_input, shadow_color_input, shadow_size_input, 
                    bold_input, italic_input, uppercase_input,
                    highlight_size_input, words_per_block_input, gap_limit_input, mode_input,
                    underline_input, strikeout_input, border_style_input,
                    vertical_pos_input, alignment_input,
                    remove_punc_input
                ]
                
                # Update manual inputs when preset changes
                preset_input.change(subs.apply_preset, inputs=[preset_input], outputs=manual_inputs)
                
                # Auto-update PREVIEW HTML on any change
                for inp in manual_inputs:
                    inp.change(subs.generate_preview_html, inputs=manual_inputs, outputs=preview_html)
                
                # Render video button
                preview_vid_btn.click(
                    subs.render_preview_video,
                    inputs=manual_inputs,
                    outputs=preview_vid
                )
                
                # Initial load
                demo.load(subs.generate_preview_html, inputs=manual_inputs, outputs=preview_html)
                demo.load(subs.apply_preset, inputs=[preset_input], outputs=manual_inputs) # Apply default preset on load

             with gr.Row():
                 start_btn = gr.Button(i18n("Start Processing"), variant="primary")
                 stop_btn = gr.Button(i18n("Stop"), variant="stop", visible=False)
             stop_btn.click(kill_process, outputs=[])
             logs_output = gr.Textbox(label=i18n("Logs"), lines=10, autoscroll=True, elem_id="logs_output")
             
             # Force scroll to bottom via JS
             logs_output.change(fn=None, inputs=[], outputs=[], js="""
                function() {
                    var ta = document.querySelector('#logs_output textarea');
                    if(ta) {
                        // Setup scroll listener once to track user intent
                        if (!ta._scrollerSetup) {
                            ta._isSticky = true; // Default to sticky
                            ta.addEventListener('scroll', function() {
                                var diff = ta.scrollHeight - ta.scrollTop - ta.clientHeight;
                                // If near bottom (<50px), enable sticky. Else disable.
                                if (diff <= 50) {
                                     ta._isSticky = true;
                                } else {
                                     ta._isSticky = false;
                                }
                            });
                            ta._scrollerSetup = true;
                        }
                        
                        // Apply scroll only if sticky
                        if(ta._isSticky === undefined || ta._isSticky === true) {
                            ta.scrollTop = ta.scrollHeight;
                        }
                    }
                }
             """)
             results_html = gr.HTML(label=i18n("Results"))
             
             # MUST pass all all new inputs to the run function
             start_btn.click(run_viral_cutter, inputs=[
                 input_source, project_selector, url_input, video_upload, segments_input, viral_input, themes_input, min_dur_input, max_dur_input, 
                 model_input, ai_backend_input, api_key_input, ai_model_input, chunk_size_input, 
                 workflow_input, face_model_input, face_mode_input, face_detect_interval_input, no_face_mode_input, 
                 tracking_alpha_input, face_filter_thresh_input, face_two_thresh_input, face_conf_thresh_input, face_dead_zone_input, focus_active_speaker_input, 
                 active_speaker_mar_input, active_speaker_score_diff_input, include_motion_input, active_speaker_motion_threshold_input, active_speaker_motion_sensitivity_input, active_speaker_decay_input,
                 use_custom_subs, 
                 # Expanded Manual Inputs mapping
                 font_name_input, font_size_input, font_color_input, highlight_color_input, 
                 outline_color_input, outline_thickness_input, shadow_color_input, shadow_size_input, 
                 bold_input, italic_input, uppercase_input, vertical_pos_input, alignment_input,
                 # New Inputs
                 highlight_size_input, words_per_block_input, gap_limit_input, mode_input, 
                 underline_input, strikeout_input, border_style_input, remove_punc_input,
                 video_quality_input, use_youtube_subs_input, translate_input
             ], outputs=[logs_output, start_btn, stop_btn, results_html])


        with gr.Tab(i18n("Subtitle Editor")):
            gr.Markdown(f"### {i18n('Edit Subtitles (Smart Mode)')}")
            
            with gr.Group():
                editor_project_dropdown = gr.Dropdown(choices=library.get_existing_projects(), label=i18n("Select Project"), value=None)
                editor_refresh_btn = gr.Button(i18n("Refresh"), size="sm")
            
            with gr.Group():
                editor_file_dropdown = gr.Dropdown(choices=[], label=i18n("Select Subtitle File"), interactive=True)
                editor_load_btn = gr.Button(i18n("Load Subtitles"), variant="secondary")

            # Hidden state to store full path of currently loaded JSON
            current_json_path = gr.State()

            # The Dataframe Editor
            # Headers: Start, End, Text
            subtitle_dataframe = gr.Dataframe(
                headers=["Start", "End", "Text"],
                datatype=["str", "str", "str"],
                col_count=(3, "fixed"),
                interactive=True,
                label=i18n("Subtitle Segments"),
                wrap=True
            )

            with gr.Row():
                editor_save_btn = gr.Button(i18n("💾 Save Changes"), variant="primary")
                editor_render_single_btn = gr.Button(i18n("⚡ Render This Segment (Very-Fast)"), variant="secondary")
                editor_render_all_btn = gr.Button(i18n("🎬 Render All (Fast)"), variant="stop")
            
            editor_status = gr.Textbox(label=i18n("Status"), interactive=False)

            # --- Callbacks for Editor ---
            editor_refresh_btn.click(library.refresh_projects, outputs=editor_project_dropdown)

            def update_file_list(proj_name):
                if not proj_name: return gr.update(choices=[])
                proj_path = os.path.join(VIRALS_DIR, proj_name)
                files = editor.list_editable_files(proj_path)
                return gr.update(choices=files, value=files[0] if files else None)

            editor_project_dropdown.change(update_file_list, inputs=editor_project_dropdown, outputs=editor_file_dropdown)

            def load_subs(proj_name, file_name):
                if not proj_name or not file_name:
                    return [], None, i18n("Please select project and file.")
                
                full_path = os.path.join(VIRALS_DIR, proj_name, 'subs', file_name)
                data = editor.load_transcription_for_editor(full_path)
                return data, full_path, i18n("Loaded {} segments.").format(len(data))

            editor_load_btn.click(load_subs, inputs=[editor_project_dropdown, editor_file_dropdown], outputs=[subtitle_dataframe, current_json_path, editor_status])

            def save_subs(json_path, df):
                if not json_path: return i18n("No file loaded.")
                data_list = df.values.tolist() if hasattr(df, 'values') else df
                msg = editor.save_editor_changes(json_path, data_list)
                return msg

            editor_save_btn.click(save_subs, inputs=[current_json_path, subtitle_dataframe], outputs=editor_status)

            def render_single(json_path, use_custom, font_name, font_size, font_color, highlight_color, 
                              outline_color, outline_thickness, shadow_color, shadow_size, 
                              is_bold, is_italic, is_uppercase, 
                              h_size, w_block, gap, mode, under, strike, border_s, 
                              vertical_pos, alignment, remove_punc):
                
                if not json_path: return i18n("No file loaded.")
                
                subtitle_config_path = os.path.join(WORKING_DIR, "temp_subtitle_config.json")
                
                # Save config if custom subs enabled
                if use_custom:
                    subtitle_config = {
                        "font": font_name, "base_size": int(font_size), 
                        "base_color": convert_color_to_ass(font_color), 
                        "highlight_color": convert_color_to_ass(highlight_color),
                        "outline_color": convert_color_to_ass(outline_color), 
                        "outline_thickness": outline_thickness, 
                        "shadow_color": convert_color_to_ass(shadow_color),
                        "shadow_size": shadow_size, "vertical_position": vertical_pos, 
                        "alignment": alignment, "bold": 1 if is_bold else 0, 
                        "italic": 1 if is_italic else 0, 
                        "underline": 1 if under else 0, "strikeout": 1 if strike else 0, 
                        "border_style": border_s, "words_per_block": int(w_block), 
                        "gap_limit": gap, "mode": mode, "highlight_size": int(h_size),
                        "uppercase": 1 if is_uppercase else 0,
                        "remove_punctuation": remove_punc
                    }
                    try:
                        with open(subtitle_config_path, "w", encoding="utf-8") as f:
                            json.dump(subtitle_config, f, indent=4)
                    except Exception: pass
                else:
                    # Remove temp config if it exists to ensure defaults are used
                    try:
                        if os.path.exists(subtitle_config_path):
                            os.remove(subtitle_config_path)
                    except Exception: pass
                
                # We expect user to SAVE first, but we could auto-save.
                # For now assume saved.
                msg = editor.render_specific_video(json_path)
                return msg

            editor_render_single_btn.click(
                render_single, 
                inputs=[current_json_path, use_custom_subs] + manual_inputs, 
                outputs=editor_status
            )

            def render_all(proj_name, use_custom, font_name, font_size, font_color, highlight_color, 
                           outline_color, outline_thickness, shadow_color, shadow_size, 
                           is_bold, is_italic, is_uppercase, 
                           h_size, w_block, gap, mode, under, strike, border_s, 
                           vertical_pos, alignment, remove_punc):
                if not proj_name: return i18n("No project selected.")
                
                # Save config
                if use_custom:
                    subtitle_config = {
                        "font": font_name, "base_size": int(font_size), 
                        "base_color": convert_color_to_ass(font_color), 
                        "highlight_color": convert_color_to_ass(highlight_color),
                        "outline_color": convert_color_to_ass(outline_color), 
                        "outline_thickness": outline_thickness, 
                        "shadow_color": convert_color_to_ass(shadow_color),
                        "shadow_size": shadow_size, "vertical_position": vertical_pos, 
                        "alignment": alignment, "bold": 1 if is_bold else 0, 
                        "italic": 1 if is_italic else 0, 
                        "underline": 1 if under else 0, "strikeout": 1 if strike else 0, 
                        "border_style": border_s, "words_per_block": int(w_block), 
                        "gap_limit": gap, "mode": mode, "highlight_size": int(h_size),
                        "uppercase": 1 if is_uppercase else 0,
                        "remove_punctuation": remove_punc
                    }
                    subtitle_config_path = os.path.join(WORKING_DIR, "temp_subtitle_config.json")
                    try:
                        with open(subtitle_config_path, "w", encoding="utf-8") as f:
                            json.dump(subtitle_config, f, indent=4)
                    except Exception: pass

                proj_path = os.path.join(VIRALS_DIR, proj_name)
                
                # IMPORTANT: Pass the config file path to the command
                subtitle_config_path = os.path.join(WORKING_DIR, "temp_subtitle_config.json")
                cmd = [sys.executable, MAIN_SCRIPT_PATH, "--project-path", proj_path, "--workflow", "3", "--skip-prompts"]
                
                if use_custom and os.path.exists(subtitle_config_path):
                     cmd.extend(["--subtitle-config", subtitle_config_path])

                try:
                    subprocess.Popen(cmd, cwd=WORKING_DIR)
                    return i18n("Render All started in background... Check terminal/logs.")
                except Exception as e:
                    return i18n("Error starting render: {}").format(e)

            editor_render_all_btn.click(
                render_all, 
                inputs=[editor_project_dropdown, use_custom_subs] + manual_inputs, 
                outputs=editor_status
            )


        with gr.Tab(i18n("Library")):
            gr.Markdown(f"### {i18n('Existing Projects')}")
            with gr.Row():
                project_dropdown = gr.Dropdown(choices=library.get_existing_projects(), label=i18n("Select Project"), value=None)
                refresh_btn = gr.Button(i18n("Refresh List"))
            project_gallery_html = gr.HTML()
            refresh_btn.click(library.refresh_projects, outputs=project_dropdown)
            def on_select_project(proj_name): return library.generate_project_gallery(proj_name)
            project_dropdown.change(on_select_project, project_dropdown, project_gallery_html)
    
    gr.Markdown(f"""
        <hr>
        <div style='text-align: center; font-size: 0.9em; color: #777;'>
            <p>
                <strong>{i18n('Desenvolvido por Rafael Godoy')}</strong>
                <br>
                {i18n('Apoie o projeto, qualquer valor é bem-vindo:')} 
                <a href='https://nubank.com.br/pagar/1ls6a4/0QpSSbWBSq' target='_blank'><strong>{i18n('Apoiar via PIX')}</strong></a>
                <br>
                {i18n('100% local • open source • no subscription required')} 
            </p>
        </div>
        """)
if __name__ == "__main__":
    import webbrowser
    import threading
    import time
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--colab", action="store_true", help="Run in Google Colab mode")
    parser.add_argument("--face-model", default="insightface", help="Default face model (env var VIRALCUTTER_FACE_MODEL takes precedence for UI default)")
    args = parser.parse_args()

    if args.colab:
        print("Running in Colab mode. Generating public link with Static Mounts...")
        library.set_url_mode("fastapi")
        
        # Broaden allowed paths for Colab
        allowed_dirs = [VIRALS_DIR, WORKING_DIR, os.getcwd(), "."]
        
        # Explicitly set static paths
        try:
            gr.set_static_paths(paths=allowed_dirs)
            print(f"DEBUG: Registered static paths: {allowed_dirs}")
        except AttributeError:
            print("DEBUG: gr.set_static_paths not available")
        
        print(f"DEBUG: Allowed paths for Gradio: {allowed_dirs}")
        
        # Launch with prevent_thread_lock to allow mounting
        app, local_url, share_url = demo.queue().launch(
            share=True, 
            allowed_paths=allowed_dirs,
            prevent_thread_lock=True
        )
        
        # Mount the VIRALS directory explicitly
        app.mount("/virals", StaticFiles(directory=VIRALS_DIR), name="virals")
        print(f"Mounted /virals to {VIRALS_DIR}")
        
        demo.block_thread()
    else:
        # Check environment
        is_windows = (os.name == 'nt')
        
        library.set_url_mode("fastapi")
        allowed_dirs = [VIRALS_DIR, WORKING_DIR, os.getcwd(), "."]
        try:
            gr.set_static_paths(paths=allowed_dirs)
        except AttributeError: pass
        
        from fastapi.responses import FileResponse
        from fastapi import BackgroundTasks

        # Helper to attach routes to any FastAPI app (whether created by Gradio or us)
        def attach_extra_routes(fastapi_app):
            fastapi_app.mount("/virals", StaticFiles(directory=VIRALS_DIR), name="virals")
            
            @fastapi_app.get("/export_xml_api")
            def export_xml_api(project: str, segment: int, background_tasks: BackgroundTasks, format: str = "premiere"):
                try:
                    project_path = os.path.join(VIRALS_DIR, project)
                    script_path = os.path.join(WORKING_DIR, "scripts", "export_xml.py")
                    cmd = [sys.executable, script_path, "--project", project_path, "--segment", str(segment), "--format", format]
                    subprocess.run(cmd, check=True)
                    proj_name = os.path.basename(project_path)
                    zip_filename = f"export_{proj_name}_seg{segment}.zip"
                    file_path = os.path.join(project_path, zip_filename)
                    if os.path.exists(file_path):
                        return FileResponse(file_path, filename=zip_filename, media_type='application/zip')
                    else:
                        return {"error": f"File generation failed. Expected: {file_path}"}
                except Exception as e:
                    return {"error": str(e)}
            
            print(f"Mounted /virals to {VIRALS_DIR}")

        if is_windows:
            print("Running in Windows environment (using Gradio launch for convenience).")
            # Windows: Use demo.launch() for convenience (auto-browser, etc)
            app, local_url, share_url = demo.queue().launch(
                share=False, 
                allowed_paths=allowed_dirs, 
                inbrowser=True,
                server_name="0.0.0.0",
                server_port=7860,
                prevent_thread_lock=True
            )
            attach_extra_routes(app)
            demo.block_thread()
        else:
            print("Running in Linux/Container environment (using Uvicorn for stability).")
            # Linux/HF: Use Uvicorn for explicit loop control
            app = FastAPI()
            attach_extra_routes(app)
            # Disable SSR to prevent Node proxying issues on HF Spaces
            app = gr.mount_gradio_app(app, demo.queue(), path="/", allowed_paths=allowed_dirs, ssr_mode=False)
            uvicorn.run(app, host="0.0.0.0", port=7860)
