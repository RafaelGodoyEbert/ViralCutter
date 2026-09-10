import os
import json
import shutil
import zipfile
from .utils import json_to_srt, get_video_dims
from .face_detection import detect_faces_jit
from .rendering import render_segmented_overlays
from .xml_generator import create_premiere_xml

def export_pack(project_path, segment_index, output_format="premiere"):
    """
    Generates a ZIP Pack for the segment.
    """
    print(f"Starting Export Pack for Project: {os.path.basename(project_path)}, Segment: {segment_index}")
    
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
        print(f"Error: No video file found for segment {segment_index} in {cut_dir}")
        return
        
    print(f"Selected Video: {video_file}")

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
                        print(f"Found Face Coordinates: {f}")
                except Exception as e:
                    print(f"Face coords load error: {e}")
                break
    
    if face_data is None:
        print("No pre-computed face data found. Attempting JIT detection...")
        face_data = detect_faces_jit(video_file)

    # 3. PREPARE STAGING
    export_name = f"export_{proj_name}_seg{segment_index}"
    stage_dir = os.path.join(project_path, export_name)
    
    if os.path.exists(stage_dir):
        try:
            shutil.rmtree(stage_dir)
        except Exception:
            import random
            stage_dir += f"_{random.randint(1000,9999)}"
            
    os.makedirs(stage_dir, exist_ok=True)
    
    # 4. COPY VIDEO (Prefer Original Scale for XML editing)
    source_video_to_copy = video_file
    dest_filename = "video_cut.mp4"
    
    # Try to find original scale version in 'cuts' folder
    # video_file is usually in 'cuts', lets check there
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
            print(f"Using Original Scale Source for Export: {original_scale_candidate}")
            source_video_to_copy = original_scale_candidate
            dest_filename = "video_source.mp4" # Distinct name
    except Exception as e:
        print(f"Error checking for original scale video: {e}")
    
    dest_video = os.path.join(stage_dir, dest_filename)
    shutil.copy2(source_video_to_copy, dest_video)
    
    # 5. RENDER OVERLAYS (SEGMENTED)
    overlay_segments = []
    if ass_file and json_file:
         try:
             with open(json_file, 'r', encoding='utf-8') as f:
                 jdata = json.load(f)
             
             # Extract segment list
             jdata_segs = []
             if isinstance(jdata, dict) and "segments" in jdata:
                 jdata_segs = jdata["segments"]
             elif isinstance(jdata, list):
                 jdata_segs = jdata
             
             if jdata_segs:
                 # Create 'captions' subfolder for organization
                 captions_dir = os.path.join(stage_dir, "captions")
                 os.makedirs(captions_dir, exist_ok=True)
                 
                 # Render into subfolder
                 overlay_segments = render_segmented_overlays(ass_file, jdata_segs, video_file, captions_dir)
             
         except Exception as e:
             print(f"Error preparing overlay segments: {e}")
    else:
        print("Missing ASS or JSON for subtitles. Skipping overlays.")

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

    # 7. GENERATE XML
    width_src, height_src, frames, fps = get_video_dims(dest_video)
    
    # Validation for resolution mismatch (same as before)
    if face_data:
        max_x = 0
        for entry in face_data:
            for f in entry.get('faces', []):
                if len(f) >= 3 and f[2] > max_x: max_x = f[2]
        if max_x > width_src:
            print(f"Correction: Detecting 4K source based on face coords ({max_x} > {width_src})")
            width_src = 3840
            height_src = 2160
         # 6. XML GENERATION
    width, height, duration, fps = get_video_dims(video_file)
    
    print(f"DEBUG: Passing face_data to XML: {len(face_data) if face_data else 'None'}")
    
    # Logic to Determine Sequence Resolution
    # Default 1080p Vertical
    seq_w = 1080
    seq_h = 1920
    
    # If source is 4K (Width > 2000 or Height > 2000), upgrade to 4K Vertical
    # Note: width_src from 'get_video_dims' usually returns width. 
    # Normal 4K is 3840x2160.
    if width_src > 3000 or height_src > 3000:
        print("Detected 4K Source Content. Setting Sequence to 4K Vertical (2160x3840).")
        seq_w = 2160
        seq_h = 3840
    else:
        print("Source is 1080p or lower. Setting Sequence to 1080p Vertical (1080x1920).")

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
        source_height=height_src
    )
    
    xml_output = os.path.join(stage_dir, "timeline.xml")
    with open(xml_output, "w", encoding="utf-8") as f:
        f.write(xml_content)
        
    print("Generated Custom Premiere XML (Opus-Style Segments).")

    # 8. ZIP IT
    zip_path = f"{stage_dir}.zip"
    shutil.make_archive(stage_dir, 'zip', stage_dir)
    
    print(f"SUCCESS: Export Pack created at {zip_path}")
    
    # Cleanup
    try:
        # shutil.rmtree(stage_dir)
        pass
    except: pass
    
    return zip_path
