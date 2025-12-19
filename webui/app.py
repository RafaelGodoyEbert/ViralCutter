import gradio as gr
import subprocess
import os
import sys
import json
import psutil
import datetime
import time
import urllib.parse
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

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

# Ensure VIRALS dir exists
if not os.path.exists(VIRALS_DIR):
    os.makedirs(VIRALS_DIR, exist_ok=True)

# Global variables
current_process = None

# Helpers
def convert_color_to_ass(hex_color, alpha="00"):
    if not hex_color or not hex_color.startswith("#"):
        return f"&H{alpha}FFFFFF&"
    hex_clean = hex_color.lstrip('#')
    if len(hex_clean) == 6:
        r = hex_clean[0:2]
        g = hex_clean[2:4]
        b = hex_clean[4:6]
        return f"&H{alpha}{b}{g}{r}&"
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
    'gpt-4o-mini',
    'gpt-4'
]


def update_ai_settings(backend):
    if backend == "gemini":
        return gr.update(choices=GEMINI_MODELS, value=GEMINI_MODELS[1], visible=True), gr.update(value=20000, visible=True)
    elif backend == "g4f":
        return gr.update(choices=G4F_MODELS, value=G4F_MODELS[0], visible=True), gr.update(value=2000, visible=True)
    else:
        # Manual
        return gr.update(visible=False), gr.update(visible=False)

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


def run_viral_cutter(input_source, project_name, url, segments, viral, themes, min_duration, max_duration, model, ai_backend, api_key, ai_model_name, chunk_size, workflow, face_model, face_mode, face_detect_interval, 
                     face_filter_thresh, face_two_thresh, face_conf_thresh, face_dead_zone, focus_active_speaker, active_speaker_mar, active_speaker_score_diff, include_motion, active_speaker_motion_threshold, active_speaker_motion_sensitivity, active_speaker_decay,
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
    cmd.extend(["--face-model", face_model])
    cmd.extend(["--face-mode", face_mode])
    if face_detect_interval: cmd.extend(["--face-detect-interval", str(face_detect_interval)])
    
    # New Face Params
    if face_filter_thresh is not None: cmd.extend(["--face-filter-threshold", str(face_filter_thresh)])
    if face_two_thresh is not None: cmd.extend(["--face-two-threshold", str(face_two_thresh)])
    if face_conf_thresh is not None: cmd.extend(["--face-confidence-threshold", str(face_conf_thresh)])
    if face_dead_zone is not None: cmd.extend(["--face-dead-zone", str(face_dead_zone)])


    
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
    current_process = subprocess.Popen(cmd, cwd=WORKING_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, env=env)
    logs = ""
    project_folder_path = None
    if input_source == "Existing Project" and project_name:
         # If using existing project, we already know the path, but let's see if logs confirm it
         project_folder_path = os.path.join(VIRALS_DIR, project_name)

    for line in current_process.stdout:
        logs += line
        if "Project Folder:" in line:
            parts = line.split("Project Folder:")
            if len(parts) > 1: project_folder_path = parts[1].strip()
        yield logs, gr.update(visible=True, interactive=False), gr.update(visible=True), None
    
    if current_process:
        current_process.wait()
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

/* Hide Footer */
footer {visibility: hidden}

/* Container Width */
.gradio-container {
    max-width: 98% !important; 
    margin: 0 auto;
}
"""

import header

with gr.Blocks(title=i18n("ViralCutter WebUI"), theme=gr.themes.Default(primary_hue="blue", neutral_hue="slate"), css=css) as demo:
    gr.Markdown(header.badges)
    gr.Markdown(header.description)
    with gr.Tabs():
        with gr.Tab(i18n("Create New")):
             with gr.Row():
                with gr.Column(scale=1):
                    input_source = gr.Radio([(i18n("YouTube URL"), "YouTube URL"), (i18n("Existing Project"), "Existing Project")], label=i18n("Input Source"), value="YouTube URL")
                    
                    url_input = gr.Textbox(label=i18n("YouTube URL"), placeholder="https://www.youtube.com/watch?v=...", visible=True)
                    
                    with gr.Row():
                        video_quality_input = gr.Dropdown(choices=["best", "1080p", "720p", "480p"], label=i18n("Video Quality"), value="best")
                        translate_input = gr.Dropdown(choices=["None", "pt", "en", "es", "fr", "de", "it", "ru", "ja", "ko", "zh-CN"], label=i18n("Translate Subtitles To"), value="None")
                        use_youtube_subs_input = gr.Checkbox(label=i18n("Use YouTube Subs"), value=True, info=i18n("Download and use official subtitles if available. (Recommended, it speeds up the process)"))

                    project_selector = gr.Dropdown(choices=[], label=i18n("Select Project"), visible=False)
                    
                    def on_source_change(source):
                        if source == i18n("YouTube URL"):
                            return gr.update(visible=True), gr.update(visible=False), gr.update(value="Full") # Reset to Full if URL is picked? Optional.
                        else:
                            # Load projects
                            projs = library.get_existing_projects()
                            return gr.update(visible=False), gr.update(choices=projs, visible=True), gr.update(value="Subtitles Only") # Auto-switch to Subs Only
                    
                    
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
                        ai_backend_input = gr.Dropdown(choices=[(i18n("Gemini"), "gemini"), (i18n("G4F"), "g4f"), (i18n("Manual"), "manual")], label=i18n("AI Backend"), value="gemini")
                        api_key_input = gr.Textbox(label=i18n("Gemini API Key"), type="password")
                    
                    # New Dynamic Inputs
                    with gr.Row():
                        ai_model_input = gr.Dropdown(choices=GEMINI_MODELS, label=i18n("AI Model"), value=GEMINI_MODELS[1], allow_custom_value=True)
                        chunk_size_input = gr.Number(label=i18n("Chunk Size"), value=20000, precision=0)
                    
                    # Update logic
                    ai_backend_input.change(update_ai_settings, inputs=ai_backend_input, outputs=[ai_model_input, chunk_size_input])

                    model_input = gr.Dropdown(["tiny", "small", "medium", "large", "large-v1", "large-v2", "large-v3", "turbo", "large-v3-turbo", "distil-large-v2", "distil-medium.en", "distil-small.en", "distil-large-v3"], label=i18n("Whisper Model"), value="large-v3-turbo")
                    with gr.Row():
                        workflow_input = gr.Dropdown(choices=[(i18n("Full"), "Full"), (i18n("Cut Only"), "Cut Only"), (i18n("Subtitles Only"), "Subtitles Only")], label=i18n("Workflow"), value="Full")
                        face_model_input = gr.Dropdown(["insightface", "mediapipe"], label=i18n("Face Model"), value="insightface")
                    with gr.Row():
                        face_mode_input = gr.Dropdown(choices=[(i18n("Auto"), "auto"), ("1", "1"), ("2", "2")], label=i18n("Face Mode"), value="auto")
                        face_detect_interval_input = gr.Textbox(label=i18n("Face Det. Interval"), value="0.17,1.0")
                    
                    
                    # Update listeners now that all components are defined
                    input_source.change(on_source_change, inputs=input_source, outputs=[url_input, project_selector, workflow_input])
             
             with gr.Accordion(i18n("Advanced Face Settings"), open=False):
                 face_preset_input = gr.Dropdown(choices=list(FACE_PRESETS.keys()), label=i18n("Configuration Presets"), value="Default (Balanced)", interactive=True)
                 with gr.Row():
                      face_filter_thresh_input = gr.Slider(label=i18n("Ignore Small Faces (0.0 - 1.0)"), minimum=0.0, maximum=1.0, value=0.35, step=0.05, info=i18n("Relative size to ignore background."))
                      face_two_thresh_input = gr.Slider(label=i18n("Threshold for 2 Faces (0.0 - 1.0)"), minimum=0.0, maximum=1.0, value=0.60, step=0.05, info=i18n("Size of 2nd face to activate split mode."))
                      face_conf_thresh_input = gr.Slider(label=i18n("Minimum Confidence (0.0 - 1.0)"), minimum=0.0, maximum=1.0, value=0.40, step=0.05, info=i18n("Ignore detections with low confidence."))
                      face_dead_zone_input = gr.Slider(label=i18n("Dead Zone (Stabilization)"), minimum=0, maximum=200, value=150, step=5, info=i18n("Movement pixels to ignore."))
                 
                 face_preset_input.change(apply_face_preset, inputs=face_preset_input, outputs=[face_filter_thresh_input, face_two_thresh_input, face_conf_thresh_input, face_dead_zone_input])

                 with gr.Accordion(i18n("Experimental: Active Speaker & Motion"), open=False):
                        experimental_preset_input = gr.Dropdown(choices=list(EXPERIMENTAL_PRESETS.keys()), label=i18n("Configuration Presets"), value="Default (Off)", interactive=True)
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
                preset_input = gr.Dropdown(choices=[(i18n("Manual"), "Manual")] + [(k, k) for k in subs.SUBTITLE_PRESETS.keys()], label=i18n("Quick Presets"), value="Hormozi (Classic)")
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
             logs_output = gr.Textbox(label=i18n("Logs"), lines=10, autoscroll=True)
             results_html = gr.HTML(label=i18n("Results"))
             
             # MUST pass all all new inputs to the run function
             start_btn.click(run_viral_cutter, inputs=[
                 input_source, project_selector, url_input, segments_input, viral_input, themes_input, min_dur_input, max_dur_input, 
                 model_input, ai_backend_input, api_key_input, ai_model_input, chunk_size_input, 
                 workflow_input, face_model_input, face_mode_input, face_detect_interval_input, 
                 face_filter_thresh_input, face_two_thresh_input, face_conf_thresh_input, face_dead_zone_input, focus_active_speaker_input, 
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
                    return f"Error starting render: {e}"

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
    args = parser.parse_args()

    if args.colab:
        print("Running in Colab mode. Generating public link...")
        library.set_url_mode("gradio")
        
        # Broaden allowed paths for Colab to avoid permission issues
        allowed_dirs = [VIRALS_DIR, WORKING_DIR]
        
        # Explicitly set static paths for newer Gradio versions
        try:
            gr.set_static_paths(paths=allowed_dirs)
            print(f"DEBUG: Registered static paths: {allowed_dirs}")
        except AttributeError:
            print("DEBUG: gr.set_static_paths not available (older Gradio version?)")
        
        print(f"DEBUG: Allowed paths for Gradio: {allowed_dirs}")
        
        # In Colab/Gradio mode, we launch the blocks directly with share=True
        # allowed_paths is needed to serve files via /file/ mechanism
        demo.queue().launch(share=True, allowed_paths=allowed_dirs)
    else:
        def open_browser():
            time.sleep(1.5) # Slight delay to ensure server finds port
            webbrowser.open("http://localhost:7860")

        # Create FastAPI app and mount both StaticFiles and Gradio
        fast_app = FastAPI()
        fast_app.mount("/virals", StaticFiles(directory=VIRALS_DIR), name="virals")
        
        # Mount Gradio app
        # Note: 'demo' here refers to the gr.Blocks object defined above
        app = gr.mount_gradio_app(fast_app, demo, path="/")
        
        print("Starting ViralCutter WebUI...")
        threading.Thread(target=open_browser, daemon=True).start()
        
        # Run server
        try:
            uvicorn.run(app, host="0.0.0.0", port=7860)
        except Exception as e:
            print(f"Error starting server: {e}")
            input("Press Enter to close...")

