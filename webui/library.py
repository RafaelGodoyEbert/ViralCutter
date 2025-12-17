import os
import json
import urllib.parse
import gradio as gr

# Setup Virals Dir relative to this file
# This file is in webui/library.py
# VIRALS dir is in ../VIRALS (root of project)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.append(BASE_DIR)
from i18n.i18n import I18nAuto
i18n = I18nAuto()

VIRALS_DIR = os.path.join(BASE_DIR, "VIRALS")


# URL Mode: "fastapi" (default) or "gradio"
URL_MODE = "fastapi"

def set_url_mode(mode):
    global URL_MODE
    URL_MODE = mode

def get_existing_projects():
    if not os.path.exists(VIRALS_DIR):
        return []
    try:
        projects = [d for d in os.listdir(VIRALS_DIR) if os.path.isdir(os.path.join(VIRALS_DIR, d))]
        projects.sort(key=lambda x: os.path.getctime(os.path.join(VIRALS_DIR, x)), reverse=True)
        return projects
    except:
        return []

def refresh_projects():
    projs = get_existing_projects()
    return gr.update(choices=projs, value=projs[0] if projs else None)

def generate_project_gallery(project_path_name, is_full_path=False):
    """
    Generates HTML gallery for a given project folder using FastAPI Static Files mounting.
    """
    if not project_path_name:
        return f'<div style="padding: 20px; text-align: center;">{i18n("No project selected.")}</div>'
    
    # Determine absolute path to project folder
    if is_full_path:
        project_folder_path = project_path_name
    else:
        project_folder_path = os.path.join(VIRALS_DIR, project_path_name)

    if not os.path.exists(project_folder_path):
        return f'<div style="padding: 20px; text-align: center;">{i18n("Project path not found: {}").format(project_folder_path)}</div>'

    try:
        # Load JSON
        json_path = os.path.join(project_folder_path, "viral_segments.txt")
        segments_data = {}
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                segments_data = json.load(f)
        
        segments_list = segments_data.get("segments", [])
        
        # Fallback if list is empty
        if not segments_list:
             found_files = []
             for subdir in ["burned_sub", "cuts", "."]:
                 d = os.path.join(project_folder_path, subdir)
                 if os.path.exists(d):
                     for f in os.listdir(d):
                         if f.endswith(".mp4") and "input" not in f.lower():
                             found_files.append(os.path.join(d, f))
             found_files = sorted(list(set(found_files)))
             segments_list = [{"title": os.path.basename(f), "score": "N/A", "description": "No metadata found.", "filepath": f} for f in found_files]

        html_cards = ""
        
        for i, seg in enumerate(segments_list):
            title = seg.get("title", f"{i18n('Segment')} {i+1}")
            score = seg.get("score", "N/A")
            description = seg.get("description", i18n("No description available."))
            
            video_path = seg.get("filepath", None)
            
            # Smart search
            if not video_path:
                idx_str = f"{i:03d}"
                potential_paths = [
                    os.path.join(project_folder_path, "burned_sub", f"final-output{idx_str}_processed_subtitled.mp4"),
                    os.path.join(project_folder_path, "burned_sub", f"output{idx_str}.mp4"),
                    os.path.join(project_folder_path, f"final-output{idx_str}_processed.mp4"),
                    os.path.join(project_folder_path, f"output{idx_str}_original_scale.mp4"),
                    os.path.join(project_folder_path, f"output{idx_str}.mp4"),
                    os.path.join(project_folder_path, "cuts", f"output{idx_str}_original_scale.mp4"),
                    os.path.join(project_folder_path, "cuts", f"segment_{idx_str}.mp4"),
                    os.path.join(project_folder_path, "cuts", f"{idx_str}.mp4")
                ]
                if isinstance(seg.get("filename"), str):
                    potential_paths.insert(0, os.path.join(project_folder_path, seg["filename"]))
                    potential_paths.insert(0, os.path.join(project_folder_path, "burned_sub", seg["filename"]))

                for p in potential_paths:
                    if os.path.exists(p):
                        video_path = p
                        break
            
            # Loose search
            if not video_path:
                 sub_dirs = [os.path.join(project_folder_path, "burned_sub"), os.path.join(project_folder_path, "cuts")]
                 for sd in sub_dirs:
                     if os.path.exists(sd):
                         for f in sorted(os.listdir(sd)):
                             idx_str = f"{i:03d}"
                             if f.endswith(".mp4") and idx_str in f:
                                 video_path = os.path.join(sd, f)
                                 break
                     if video_path: break

            video_tag = ""
            download_link = ""
            if video_path:
                try:
                    abs_video = os.path.abspath(video_path)
                    
                    if URL_MODE == "gradio":
                         # Gradio Launch Mode
                         # Strategy: STRICT RELATIVE PATH
                         # With gr.set_static_paths in place, standard /file/relative should work.
                         
                         cwd = os.getcwd()
                         norm_path = os.path.normpath(abs_video).replace("\\", "/")
                         
                         try:
                             rel_path = os.path.relpath(norm_path, cwd).replace("\\", "/")
                         except:
                             rel_path = norm_path
                         
                         rel_path_clean = rel_path.lstrip("/")
                         path_encoded = urllib.parse.quote(rel_path_clean, safe="/:")
                         video_src = f"/file/{path_encoded}"
                         
                         # Debug Logging
                         print(f"DEBUG: URL Generation (Strict Relative)")
                         print(f"DEBUG:   CWD: {cwd}")
                         print(f"DEBUG:   Rel Path: {rel_path_clean}")
                         print(f"DEBUG:   Result: {video_src}")
                         
                         if os.path.exists(norm_path):
                             print(f"DEBUG:   File Exists.")
                         else:
                             print(f"DEBUG:   File NOT FOUND.")
                             
                         video_tag = f"""
                        <video controls preload="metadata" playsinline style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain;">
                            <source src="{video_src}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                        """
                         download_link = f'<a href="{video_src}" target="_blank" download="{os.path.basename(video_path)}" style="color: #aaa; display: flex; align-items: center; justify-content: center; padding: 5px; border-radius: 50%; transition: color 0.2s;" title="Download" onmouseover="this.style.color=\'#fff\'" onmouseout="this.style.color=\'#aaa\'"><svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg></a>'

                    else:
                        # Use Relative Path through /virals mount
                        # Calculate relative path from VIRALS_DIR
                        # video_path needs to be under VIRALS_DIR for this to work
                        abs_virals = os.path.abspath(VIRALS_DIR)
                        
                        if abs_video.startswith(abs_virals):
                            rel_path = os.path.relpath(abs_video, abs_virals)
                            # Replace backslashes for URL
                            url_path = rel_path.replace("\\", "/")
                            url_path = urllib.parse.quote(url_path)
                            
                            # Add timestamp to force cache refresh
                            import time
                            timestamp = int(time.time())
                            video_src = f"/virals/{url_path}?t={timestamp}"
                            
                            video_tag = f"""
                            <video controls preload="metadata" playsinline style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain;">
                                <source src="{video_src}" type="video/mp4">
                                Your browser does not support the video tag.
                            </video>
                            """
                            
                            download_link = f'<a href="{video_src}" download="{os.path.basename(video_path)}" style="color: #aaa; display: flex; align-items: center; justify-content: center; padding: 5px; border-radius: 50%; transition: color 0.2s;" title="Download" onmouseover="this.style.color=\'#fff\'" onmouseout="this.style.color=\'#aaa\'"><svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg></a>'
                        else:
                            video_tag = f'<div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #222; color: #666;"><span>⚠️</span><br>{i18n("External Video")}</div>'
                except Exception as e:
                    video_tag = f'<div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #222; color: #666;"><span>⚠️</span><br>{i18n("Error: {}").format(str(e))}</div>'

            else:
                video_tag = f'<div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #222; color: #666;"><span>⚠️</span><br>{i18n("Not Found")}</div>'
            
            # Score
            score_color = "#22c55e"
            try:
                if isinstance(score, int) or (isinstance(score, str) and score.isdigit()):
                    val = int(score)
                    if val < 70: score_color = "#ef4444" 
                    elif val < 85: score_color = "#eab308"
            except: pass

            # Card HTML - Dark Grid Style like Opus.pro (Inline Styles)
            card_html = f"""
            <div style="display: flex; flex-direction: column; background: transparent; overflow: visible;">
                
                <!-- Video Player Container (9:16 Aspect Ratio) -->
                <div style="position: relative; width: 100%; padding-top: 177.77%; background: #111; border-radius: 12px; overflow: hidden; margin-bottom: 12px; border: 1px solid #333; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                    {video_tag}
                </div>
                
                <!-- Info Area -->
                <div style="display: flex; flex-direction: column; gap: 6px; padding: 0 4px;">
                    <!-- Top Row: Score and Actions -->
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 28px; font-weight: 900; line-height: 1; color: {score_color}; font-family: sans-serif;">{score}</span>
                        <div style="display: flex; align-items: center;">
                            {download_link}
                        </div>
                    </div>
                    
                    <!-- Title -->
                    <h4 style="margin: 4px 0 0 0; color: #e5e5e5; font-size: 15px; font-weight: 600; line-height: 1.4; font-family: sans-serif; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-align: center;" title="{title}">{title}</h4>
                </div>
            </div>
            """
            html_cards += card_html
        
        if not html_cards:
             return f'<div style="padding: 40px; text-align: center; color: #888; font-size: 1.2em;">{i18n("No viral segments found.")}</div>'

        # Gallery Container
        return f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 30px; width: 100%; padding: 10px 0;">
            {html_cards}
        </div>
        """

    except Exception as e:
        return i18n("Error loading gallery: {}").format(e)
