
import json
import os
import re
import sys

# Import scripts for direct processing
import scripts.adjust_subtitles as adjust
import scripts.burn_subtitles as burn
import main_improved 

# Helper to format seconds to HH:MM:SS,mmm
def format_timestamp(seconds):
    millis = int((seconds % 1) * 1000)
    seconds = int(seconds)
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"

# Helper to parse HH:MM:SS,mmm back to seconds
def parse_timestamp(ts_str):
    try:
        # Handle different formats just in case
        ts_str = ts_str.replace(',', '.')
        parts = ts_str.split(':')
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        return 0.0
    except:
        return 0.0

def load_transcription_for_editor(json_path):
    """
    Loads `final-outputXXX_processed.json` and flattens it for the Dataframe editor.
    Returns a list of lists: [[Start, End, Text], ...]
    """
    if not os.path.exists(json_path):
        return []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        segments = data.get('segments', [])
        editor_data = [] # List of [Start, End, Text]

        # We display segments. Each segment has 'words'. 
        # But users want to edit at segment level (the full sentence).
        for seg in segments:
            start_fmt = format_timestamp(seg.get('start', 0))
            end_fmt = format_timestamp(seg.get('end', 0))
            text = seg.get('text', '').strip()
            editor_data.append([start_fmt, end_fmt, text])
            
        return editor_data
    except Exception as e:
        print(f"Error loading JSON for editor: {e}")
        return []

def save_editor_changes(json_path, new_data):
    """
    Reconstructs the complex JSON from the simplified Dataframe edits.
    Smartly redistributes word timestamps if text content changed.
    """
    if not os.path.exists(json_path):
        return "Error: Original file not found."

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            original_json = json.load(f)
        
        original_segments = original_json.get('segments', [])
        
        # new_data is list of [Start, End, Text] from Dataframe
        
        updated_segments = []
        
        for i, row in enumerate(new_data):
            start_str, end_str, new_text = row
            start_sec = parse_timestamp(start_str)
            end_sec = parse_timestamp(end_str)
            
            # Get original segment to recycle word timings if possible
            if i < len(original_segments):
                orig_seg = original_segments[i]
                orig_words = orig_seg.get('words', [])
            else:
                orig_seg = {}
                orig_words = []
            
            # 1. Update Segment Level
            new_segment = {
                "start": start_sec,
                "end": end_sec,
                "text": new_text
            }
            
            # 2. Reconstruct Words
            # Split new text into words
            new_word_list = new_text.split()
            reconstructed_words = []
            
            if not new_word_list:
                updated_segments.append({**new_segment, "words": []})
                continue

            # Strategy:
            # - If word count matches exactly, assign original timings 1:1.
            # - If mismatch, distribute time proportionally.
            
            if len(new_word_list) == len(orig_words):
                 # Easy mode: Just replace the "word" text, keep timing
                 for j, w_text in enumerate(new_word_list):
                     orig_w = orig_words[j]
                     reconstructed_words.append({
                         "word": w_text,
                         "start": orig_w.get("start", start_sec),
                         "end": orig_w.get("end", end_sec),
                         "score": orig_w.get("score", 0.99)
                     })
            else:
                # Hard mode: Linear Interpolation
                duration = end_sec - start_sec
                if duration <= 0: duration = 0.1
                
                word_duration = duration / len(new_word_list)
                
                current_time = start_sec
                for w_text in new_word_list:
                    w_end = current_time + word_duration
                    reconstructed_words.append({
                        "word": w_text,
                        "start": round(current_time, 3),
                        "end": round(w_end, 3),
                        "score": 0.99
                    })
                    current_time = w_end
            
            new_segment["words"] = reconstructed_words
            updated_segments.append(new_segment)
            
        # Update final JSON structure
        original_json["segments"] = updated_segments
        
        # Save Text back to file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(original_json, f, indent=4, ensure_ascii=False)
            
        return "Success: Subtitles updated."
        
    except Exception as e:
        return f"Error saving changes: {e}"

def list_editable_files(project_dir):
    """
    Scans VIRALS/{project_name}/subs/ for json files.
    """
    if not os.path.exists(project_dir):
        return []
    
    subs_dir = os.path.join(project_dir, 'subs')
    if not os.path.exists(subs_dir):
        return []
        
    # Look for files matching 'final-output...processed.json'
    files = [f for f in os.listdir(subs_dir) if f.endswith('_processed.json')]
    return sorted(files)

def render_specific_video(json_full_path):
    """
    1. Regenerate ASS for this specific JSON file.
    2. Burn ASS into the corresponding Video file.
    """
    if not json_full_path or not os.path.exists(json_full_path):
        return "Error: JSON file not found."

    project_folder = os.path.dirname(os.path.dirname(json_full_path)) # ../../ from subs/file.json
    
    # Identify key paths
    filename = os.path.basename(json_full_path)
    base_name = os.path.splitext(filename)[0] # final-output000_processed
    
    # Assuming standard structure
    ass_path = os.path.join(project_folder, "subs_ass", f"{base_name}.ass")
    os.makedirs(os.path.dirname(ass_path), exist_ok=True)
    
    # Video Path?
    # burn_subtitles iterates 'final' folder and matches name.
    # The JSON is "final-output000_processed.json".
    # The video in 'final' usually is "fina-output000.mp4" or similar?
    # Wait, edit_video generates "final-output000_processed.mp4"?
    # Let's assume the name matches exactly the JSON name.
    
    # Try finding the video file
    video_folder = os.path.join(project_folder, "final")
    video_candidate = os.path.join(video_folder, f"{base_name}.mp4")
    
    if not os.path.exists(video_candidate):
        # Try stripping "_processed" (common suffix for subtitle files)
        if base_name.endswith("_processed"):
             clean_name = base_name.replace("_processed", "")
             candidate_2 = os.path.join(video_folder, f"{clean_name}.mp4")
             if os.path.exists(candidate_2):
                 video_candidate = candidate_2
        
        # If still not found, try regex strategies
        if not os.path.exists(video_candidate):
            # Strategy A: 'output123' pattern
            match = re.search(r"output(\d+)", base_name)
            
            # Strategy B: '000_Name' pattern (digits at start)
            if not match:
                match = re.search(r"^(\d+)_", base_name)
            
            if match:
                vid_id = match.group(1)
                # Look for file containing this ID
                files = os.listdir(video_folder)
                found = None
                for f in files:
                    # Match ID in filename (either outputID or ID_Name)
                    # We check if 'output{vid_id}' or '{vid_id}_' is in the file
                    # Be careful not to match '100' with '00'
                    if (f"output{vid_id}" in f or f.startswith(f"{vid_id}_")) and f.endswith(".mp4") and "subtitled" not in f:
                         found = os.path.join(video_folder, f)
                         break
                if found:
                    video_candidate = found
                else:
                    return f"Error: Could not find video file for ID {vid_id} (from {base_name}) in {video_folder}"
            else:
                 return f"Error: Could not determine video ID from {base_name}"
    
    # Output path
    burned_folder = os.path.join(project_folder, "burned_sub")
    os.makedirs(burned_folder, exist_ok=True)
    output_video_path = os.path.join(burned_folder, f"{base_name}_subtitled.mp4")

    # Load Config
    try:
        # Try to load temp config from root, else default
        temp_config = os.path.join(os.path.dirname(os.path.dirname(project_folder)), "temp_subtitle_config.json")
        # .. from VIRALS/proj -> VIRALS -> root? No.
        # project_folder is VIRALS/proj.
        # root is ../../
        root_dir = os.path.dirname(os.path.dirname(project_folder))
        # actually project_folder is c:\...\VIRALS\proj.
        # root is c:\...\
        
        # Safer: use main_improved working dir if imported from there or app
        config_path = os.path.join(root_dir, "temp_subtitle_config.json")
        if not os.path.exists(config_path):
             config_path = None
        
        config = main_improved.get_subtitle_config(config_path)
        # Ensure 'uppercase' exists as it's not in default config of main_improved
        config['uppercase'] = config.get('uppercase', False)
        
        # Load Face Modes
        face_modes = {}
        modes_file = os.path.join(project_folder, "face_modes.json")
        if os.path.exists(modes_file):
            with open(modes_file, "r") as f:
                face_modes = json.load(f)
        
        # 1. Generate ASS
        adjust.generate_ass_from_file(json_full_path, ass_path, project_folder, **config, face_modes=face_modes)
        
        # 2. Burn Video
        success, msg = burn.burn_video_file(video_candidate, ass_path, output_video_path)
        
        if success:
             return f"Success! Rendered: {os.path.basename(output_video_path)}"
        else:
             return f"Render Failed: {msg}"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Critical Error: {e}"
