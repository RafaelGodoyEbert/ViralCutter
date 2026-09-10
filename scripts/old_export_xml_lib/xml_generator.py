import os
import uuid
import statistics

def create_premiere_xml(project_name, video_path, overlay_segments, duration_frames, width=1080, height=1920, timebase=30, video_file_id=None, audio_file_id=None, scale_value=100.0, face_data=None, source_width=1920, source_height=1080):
    """
    Generates a Premiere Pro XML with segmented cuts, supporting Dual-Track (Split Screen) for multi-face scenarios.
    """
    
    def get_uid(): return str(uuid.uuid4())[:12]
    
    if not video_file_id: video_file_id = f"file-video-{get_uid()}"
    if not audio_file_id: audio_file_id = f"file-audio-{get_uid()}"
    sequence_uuid = str(uuid.uuid4())
    
    # helper for file blocks
    def get_file_block(fid, fpath, is_audio_only=False):
       audio_blk = "" if is_audio_only else "<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics><channelcount>2</channelcount></audio>"
       width_f = int(source_width)
       height_f = int(source_height)
       return f"""<file id="{fid}"><name>{os.path.basename(fpath)}</name><pathurl>{fpath}</pathurl><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><duration>{duration_frames}</duration><media><video><samplecharacteristics><width>{width_f}</width><height>{height_f}</height><alpha>straight</alpha></samplecharacteristics></video>{audio_blk}</media></file>"""

    # --- PROCESS FACE DATA (Per Frame) ---
    # We store raw faces per frame to decide clustering later
    faces_per_frame = {} 
    
    # Dimensions for Coordinate Normalization (Default to source if not in JSON)
    coords_w = source_width
    coords_h = source_height
    
    if face_data:
        # Check for Metadata in first entry to determine Coordinate System Scale
        if len(face_data) > 0:
             first_entry = face_data[0]
             if "src_size" in first_entry:
                 try:
                     w_json, h_json = first_entry["src_size"]
                     if w_json > 0 and h_json > 0:
                         coords_w = w_json
                         coords_h = h_json
                         print(f"Coordinate System Reference: {coords_w}x{coords_h}")
                         # DO NOT overwrite source_width/source_height (Actual Media Dims)
                 except: pass

        print(f"Processing {len(face_data)} face entries for Dual-Track logic...")
        for entry in face_data:
            f_idx = entry.get('frame')
            faces = entry.get('faces', [])
            if not faces: continue
            
            processed_faces = []
            for f in faces:
                cx = (f[0] + f[2]) / 2.0
                cy = (f[1] + f[3]) / 2.0
                area = (f[2]-f[0]) * (f[3]-f[1])
                
                # Calculate Normalized Center using COORDS Dimensions
                # nx, ny are 0..1 relative to the original detection frame
                nx = cx / max(1.0, float(coords_w))
                ny = cy / max(1.0, float(coords_h))
                
                # rh uses coords_h
                rh_val = 0.1
                if len(f) > 4:
                    rh_val = float(f[4])
                else:
                    rh_val = (f[3] - f[1]) / max(1.0, float(coords_h))
                
                processed_faces.append({
                    'cx': cx, 
                    'cy': cy,
                    'nx': nx, 
                    'ny': ny,
                    'area': area,
                    'rh': rh_val 
                })
            
            faces_per_frame[f_idx] = processed_faces
    
    # Ensure source_width/height are floats for calculation later
    source_width = float(source_width)
    source_height = float(source_height)

    # --- SEGMENTATION LOGIC ---
    cuts_v1 = [] # Track 1 (Main / Left)
    cuts_v2 = [] # Track 2 (Secondary / Right)
    
    fps_float = float(timebase)
    
    # Store dynamic scale suggestion per cut if possible
    # (Not fully implemented per-cut yet, but we can compute a global or per-segment average if we stored it)
    
    if overlay_segments:
        current_frame = 0
        
        # Defaults (Normalized Centers)
        last_center_v1 = (0.5, 0.5)
        last_center_v2 = (0.5, 0.5)
        
        # We also want to track optimal scale for the segment
        last_opt_scale = None
        
        sorted_segs = sorted(overlay_segments, key=lambda x: x['start'])
        is_last_dual = False # Initialize is_last_dual

        for idx, seg in enumerate(sorted_segs):
            start_f = int(seg['start'] * fps_float)
            end_f = int(seg['end'] * fps_float)
            
            # Fill Gaps
            if start_f > current_frame:
                cuts_v1.append({"start": current_frame, "end": start_f, "center": last_center_v1, "opt_scale": last_opt_scale})
                if is_last_dual: 
                     cuts_v2.append({"start": current_frame, "end": start_f, "center": last_center_v2, "opt_scale": last_opt_scale})
                pass 
            
            # Analyze Faces
            segment_faces = []
            frame_count = 0
            dual_face_frames = 0
            
            for f_idx in range(start_f, end_f):
                if f_idx in faces_per_frame:
                    fs = faces_per_frame[f_idx]
                    segment_faces.append(fs)
                    if len(fs) >= 2:
                        dual_face_frames += 1
                frame_count += 1
            
            is_dual_track = False
            if frame_count > 0:
                dual_ratio = dual_face_frames / frame_count
                if dual_ratio > 0.3:
                    is_dual_track = True
                elif frame_count < 15 and dual_face_frames > 0:
                     is_dual_track = True
            
            center_v1 = last_center_v1
            center_v2 = last_center_v2
            
            # Coordinate lists for mode calculation
            cand_v1_x, cand_v1_y = [], []
            cand_v2_x, cand_v2_y = [], []
            cand_rh = [] # Relative heights
            
            if segment_faces:
                for fs in segment_faces:
                    # Filter Top 2 by Area
                    top_faces = sorted(fs, key=lambda x: x['area'], reverse=True)[:2]
                    # Sort by X (Left to Right)
                    fs_sorted = sorted(top_faces, key=lambda x: x['nx'])
                    
                    if is_dual_track and len(fs_sorted) >= 2:
                        # Left -> V2 (Top Track, Upper Screen)
                        # Right -> V1 (Bottom Track, Lower Screen)
                        f_left = fs_sorted[0]
                        f_right = fs_sorted[-1] 
                        
                        cand_rh.append(f_left.get('rh', 0.1))
                        cand_rh.append(f_right.get('rh', 0.1))
                        
                        if abs(f_left['nx'] - f_right['nx']) < 0.20:
                             # Fallback to single
                             f_main = max(fs, key=lambda x: x['area'])
                             cand_v1_x.append(f_main['nx'])
                             cand_v1_y.append(f_main['ny'])
                             if 'rh' in f_main: cand_rh[-2:] = [f_main['rh']]
                        else:
                            # Swap Assignment Here: 
                            # Left Face -> V2 (Top)
                            cand_v2_x.append(f_left['nx'])
                            cand_v2_y.append(f_left['ny'])
                            
                            # Right Face -> V1 (Bottom)
                            cand_v1_x.append(f_right['nx'])
                            cand_v1_y.append(f_right['ny'])
                        
                    elif fs_sorted:
                        # Single -> V1
                        f1 = max(fs_sorted, key=lambda x: x['area'])
                        cand_v1_x.append(f1['nx'])
                        cand_v1_y.append(f1['ny'])
                        cand_rh.append(f1.get('rh', 0.1))

            # Smart Scale Logic REMOVED per user request
            # We will rely on strict "Fill Split Pane Height" logic in make_video_track
            opt_scale = None
            last_opt_scale = None

            # Apply Mode (Robust avg)
            def get_mode_avg(vals):
                if not vals: return 0.5
                try: return statistics.mean(vals)
                except: return vals[0]
            
            # If after filtering we have no valid V2 candidates, revert to Single Track
            if is_dual_track and not cand_v2_x:
                is_dual_track = False
                
            if cand_v1_x:
                center_v1 = (get_mode_avg(cand_v1_x), get_mode_avg(cand_v1_y))
            
            if is_dual_track:
                if cand_v2_x:
                     center_v2 = (get_mode_avg(cand_v2_x), get_mode_avg(cand_v2_y))
                else:
                     # This branch should rarely be hit now due to check above
                     if last_center_v2 != (0.5, 0.5): center_v2 = last_center_v2
                     else: center_v2 = (center_v1[0] + 0.25, center_v1[1]) 
                
            # Append Cuts
            cuts_v1.append({"start": start_f, "end": end_f, "center": center_v1, "opt_scale": opt_scale})
            
            if is_dual_track:
                cuts_v2.append({"start": start_f, "end": end_f, "center": center_v2, "opt_scale": opt_scale})
                last_center_v2 = center_v2
                is_last_dual = True
            else:
                is_last_dual = False
            
            last_center_v1 = center_v1
            current_frame = end_f
            
        # Final gap
        if current_frame < duration_frames:
             cuts_v1.append({"start": current_frame, "end": duration_frames, "center": last_center_v1, "opt_scale": last_opt_scale})

    else:
        cuts_v1.append({"start": 0, "end": duration_frames, "center": (0.5, 0.5), "opt_scale": None})

    print(f"Generated {len(cuts_v1)} V1 cuts and {len(cuts_v2)} V2 cuts.")

    # --- GENERATE XML TRACKS ---
    dual_starts = set(c['start'] for c in cuts_v2)
    
    def make_video_track(cuts_list, track_type="main"):
        items = ""
        for cut in cuts_list:
            seg_start, seg_end = cut['start'], cut['end']
            nx, ny = cut['center'] # These are Normalized Source Coords (0..1)
            
            if seg_end - seg_start <= 0: continue
            
            is_dual = (seg_start in dual_starts)
            
            # --- DIMENSION CHECKS ---
            src_w = float(source_width)
            src_h = float(source_height)
            if src_h < 100: src_h = 1080.0 # Safety default
            
            # --- SCALE LOGIC ---
            # Fill Sequence Height (Matches User's Request for correct scaling)
            # Use the actual Sequence Height passed to create_premiere_xml
            target_h = float(height)
            
            # ALWAYS scale to fill the sequence height
            final_scale = (target_h / src_h) * 100.0
            
            # Boost scale for split screen to frame faces tighter (User request: "zoom is larger when split")
            if track_type == "secondary" or is_dual:
                final_scale *= 1.2

            if final_scale < 10.0: final_scale = 100.0
            
            s_val = final_scale / 100.0

            # --- POSITIONING LOGIC (Shift-Based) ---
            # We assume Anchor Point is (0,0) -> CENTER of Clip.
            # We want to move the Face (nx, ny) to the Target Screen Position.
            
            # 1. Face Offset from Clip Center (in Source Pixels)
            # Center of Source is 0.5, 0.5
            off_x_src = (nx - 0.5) * src_w
            off_y_src = (ny - 0.5) * src_h
            
            # 2. Face Offset in Screen Pixels (after Scale)
            off_x_seq = off_x_src * s_val
            off_y_seq = off_y_src * s_val
            
            # 3. Target Screen Position (Pixels)
            # Sequence Dimensions: width, height (e.g. 1080, 1920)
            target_screen_x = 0.5 * width # Center X
            target_screen_y = 0.5 * height # Center Y (Default)
            
            if track_type == "secondary": 
                target_screen_y = 0.25 * height # Top Quarter
            elif track_type == "main" and is_dual: 
                target_screen_y = 0.75 * height # Bottom Quarter
            
            # 4. Required Clip Center Position
            # To place Face at Target, we shift Clip Center by -Offset
            req_center_x = target_screen_x - off_x_seq
            req_center_y = target_screen_y - off_y_seq
            
            # 5. Normalize for XML (0..1 relative to Sequence)
            # XML Coordinate System is Relative to Center (0,0 is Center).
            # Absolute 0..1 maps to -0.5..0.5 in XML.
            pos_h = (req_center_x / float(width)) - 0.5
            pos_v = (req_center_y / float(height)) - 0.5
            
            seg_id = f"clipitem-video-{get_uid()}"
            
            # EXPLICITLY REMOVE Anchor Point (centerOffset) to use Default (Center of Clip).
            # We calculate pos_h/pos_v assuming we are placing the Clip Center.
            
            basic_motion = f"""<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype><parameter authoringApp="PremierePro"><parameterid>scale</parameterid><name>Scale</name><value>{final_scale:.2f}</value></parameter><parameter authoringApp="PremierePro"><parameterid>center</parameterid><name>Center</name><value><horiz>{pos_h:.5f}</horiz><vert>{pos_v:.5f}</vert></value></parameter></effect></filter>"""
            
            # --- CROP LOGIC (Pane Masking) ---
            # We calculate crops based on the Screen Boundaries of the Pane.
            # This ensures the split line is perfectly respected.
            
            crop_xml = ""
            pane_top_y = 0.0
            pane_bottom_y = float(height) # Default Full Screen
            
            should_crop = False
            
            if track_type == "secondary":
                 # Top Pane (0.0 to 0.5)
                 pane_bottom_y = height / 2.0
                 should_crop = True
            elif track_type == "main" and is_dual:
                 # Bottom Pane (0.5 to 1.0)
                 pane_top_y = height / 2.0
                 should_crop = True
            
            if should_crop:
                 # 1. Calculate Clip's Screen Coordinates
                 # req_center_y is the Screen Y of the Clip Center
                 clip_screen_h = src_h * s_val
                 clip_top_screen_y = req_center_y - (clip_screen_h / 2.0)
                 clip_bottom_screen_y = req_center_y + (clip_screen_h / 2.0)
                 
                 # 2. Calculate Required Crop in Screen Pixels
                 # Pixels to remove from Top: Distance from ClipTop to PaneTop
                 # max(0, PaneTop - ClipTop)
                 crop_top_px = max(0.0, pane_top_y - clip_top_screen_y)
                 
                 # Pixels to remove from Bottom: Distance from PaneBottom to ClipBottom
                 # max(0, ClipBottom - PaneBottom)
                 crop_bottom_px = max(0.0, clip_bottom_screen_y - pane_bottom_y)
                 
                 # 3. Convert to Source Percentage
                 # CropPx / Scale = SourcePx
                 # SourcePx / SourceHeight * 100 = %
                 pct_top = (crop_top_px / s_val) / src_h * 100.0
                 pct_bottom = (crop_bottom_px / s_val) / src_h * 100.0
                 
                 # Clamp 0-100
                 pct_top = max(0.0, min(100.0, pct_top))
                 pct_bottom = max(0.0, min(100.0, pct_bottom))
                 
                 crop_parameters = ""
                 crop_parameters += f"""<parameter authoringApp="PremierePro"><parameterid>top</parameterid><name>Top</name><value>{pct_top:.2f}</value></parameter>"""
                 crop_parameters += f"""<parameter authoringApp="PremierePro"><parameterid>bottom</parameterid><name>Bottom</name><value>{pct_bottom:.2f}</value></parameter>"""
                 
                 crop_xml = f"""<filter><effect><name>Crop</name><effectid>crop</effectid><effectcategory>transform</effectcategory><effecttype>video</effecttype><mediatype>video</mediatype>{crop_parameters}</effect></filter>"""

            items += f"""<clipitem id="{seg_id}"><name>{os.path.basename(video_path)}</name><duration>{duration_frames}</duration><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><start>{seg_start}</start><end>{seg_end}</end><in>{seg_start}</in><out>{seg_end}</out>{get_file_block(video_file_id, video_path)}{basic_motion}{crop_xml}</clipitem>"""
        return f"<track>{items}</track>"

    track_v1 = make_video_track(cuts_v1, "main")
    track_v2 = make_video_track(cuts_v2, "secondary")

    # --- OVERLAY TRACK ---
    track_overlay_block = ""
    if overlay_segments:
        overlay_clips = ""
        for seg in overlay_segments:
            # ... (overlay logic same as before)
            # Re-implement simple loop here to ensure variable scope
            start_f = int(seg['start'] * fps_float)
            end_f = int(seg['end'] * fps_float)
            clip_dur = end_f - start_f
            if clip_dur <= 0: continue
            ov_fid = f"file-ov-{seg['index']}-{get_uid()}"
            ov_cid = f"clip-ov-{seg['index']}-{get_uid()}"
            file_blk = f"""<file id="{ov_fid}"><name>{os.path.basename(seg['path'])}</name><pathurl>{seg['path']}</pathurl><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><duration>{clip_dur}</duration><media><video><samplecharacteristics><width>{width}</width><height>{height}</height><alpha>straight</alpha></samplecharacteristics></video></media></file>"""
            overlay_clips += f"""<clipitem id="{ov_cid}"><name>{os.path.basename(seg['path'])}</name><duration>{clip_dur}</duration><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><start>{start_f}</start><end>{end_f}</end><in>0</in><out>{clip_dur}</out>{file_blk}<compositemode>normal</compositemode></clipitem>"""
        track_overlay_block = f"<track>{overlay_clips}</track>"
    else:
        track_overlay_block = "<track></track>"

    # --- ASSEMBLE ---
    timecode_block = f"""<timecode><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>"""
    audio_blk = f"""<track><clipitem id="{audio_file_id}"><name>{os.path.basename(video_path)}</name><duration>{duration_frames}</duration><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><start>0</start><end>{duration_frames}</end>{get_file_block(video_file_id, video_path)}<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack></clipitem></track>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?><xmeml version="4"><sequence id="{sequence_uuid}"><name>{project_name}_CutRef</name><duration>{duration_frames}</duration><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate>{timecode_block}<media><video><format><samplecharacteristics><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><width>{width}</width><height>{height}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></format>{track_v1}{track_v2}{track_overlay_block}</video><audio>{audio_blk}</audio></media></sequence></xmeml>"""
