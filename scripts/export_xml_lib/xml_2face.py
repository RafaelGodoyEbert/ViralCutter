import os
import uuid
import statistics
from xml.sax.saxutils import escape

# Import common utilities
from . import xml_common as xc

def generate_xml_2face(project_name, video_path, overlay_segments, duration_frames, width=1080, height=1920, timebase=30, video_file_id=None, audio_file_id=None, scale_value=100.0, face_data=None, source_width=1920, source_height=1080, subtitle_data=None, subtitle_config=None, face_mode="2"):
    """
    Generates Premiere Pro XML for TWO-FACE scenarios (Split Screen / Dual Track).
    """
    
    if not video_file_id: video_file_id = f"file-video-{xc.get_uid()}"
    if not audio_file_id: audio_file_id = f"file-audio-{xc.get_uid()}"
    sequence_uuid = str(uuid.uuid4())
    
    # Process Face Data
    faces_per_frame = {}
    coords_w = source_width
    coords_h = source_height
    
    if face_data:
        if len(face_data) > 0 and "src_size" in face_data[0]:
             try:
                 w_json, h_json = face_data[0]["src_size"]
                 if w_json > 0 and h_json > 0:
                     coords_w = w_json
                     coords_h = h_json
             except: pass

        for entry in face_data:
            f_idx = entry.get('frame')
            faces = entry.get('faces', [])
            if not faces: continue
            
            processed_faces = []
            for f in faces:
                cx = (f[0] + f[2]) / 2.0
                cy = (f[1] + f[3]) / 2.0
                area = (f[2]-f[0]) * (f[3]-f[1])
                nx = cx / max(1.0, float(coords_w))
                ny = cy / max(1.0, float(coords_h))
                
                rh_val = 0.1
                if len(f) > 4: rh_val = float(f[4])
                else: rh_val = (f[3] - f[1]) / max(1.0, float(coords_h))
                
                processed_faces.append({'nx': nx, 'ny': ny, 'area': area, 'rh': rh_val})
            
            faces_per_frame[f_idx] = processed_faces
            
    # Segmentation for Dual Track
    cuts_v1 = []
    cuts_v2 = []
    fps_float = float(timebase)
    
    if overlay_segments:
        current_frame = 0
        last_center_v1 = (0.5, 0.5)
        last_center_v2 = (0.5, 0.5)
        is_last_dual = False
        
        sorted_segs = sorted(overlay_segments, key=lambda x: x['start'])
        
        for idx, seg in enumerate(sorted_segs):
            start_f = int(seg['start'] * fps_float)
            end_f = int(seg['end'] * fps_float)
            
            # Gap
            if start_f > current_frame:
                cuts_v1.append({"start": current_frame, "end": start_f, "center": last_center_v1})
                if is_last_dual:
                    cuts_v2.append({"start": current_frame, "end": start_f, "center": last_center_v2})
            
            # Analyze faces
            segment_faces = []
            frame_count = 0
            dual_face_frames = 0
            
            for f_idx in range(start_f, end_f):
                if f_idx in faces_per_frame:
                    fs = faces_per_frame[f_idx]
                    segment_faces.append(fs)
                    if len(fs) >= 2: dual_face_frames += 1
                frame_count += 1
            
            is_dual_track = False
            if frame_count > 0:
                if (dual_face_frames / frame_count) > 0.3: is_dual_track = True
                elif frame_count < 15 and dual_face_frames > 0: is_dual_track = True
            
            center_v1 = last_center_v1
            center_v2 = last_center_v2
            cand_v1_x, cand_v1_y = [], []
            cand_v2_x, cand_v2_y = [], []
            
            if segment_faces:
                for fs in segment_faces:
                    top_faces = sorted(fs, key=lambda x: x['area'], reverse=True)[:2]
                    fs_sorted = sorted(top_faces, key=lambda x: x['nx'])
                    
                    if is_dual_track and len(fs_sorted) >= 2:
                        f_left = fs_sorted[0]
                        f_right = fs_sorted[-1]
                        
                        if abs(f_left['nx'] - f_right['nx']) < 0.20:
                             # Fallback to single if too close
                             f_main = max(fs, key=lambda x: x['area'])
                             cand_v1_x.append(f_main['nx'])
                             cand_v1_y.append(f_main['ny'])
                        else:
                            cand_v2_x.append(f_left['nx'])
                            cand_v2_y.append(f_left['ny'])
                            cand_v1_x.append(f_right['nx'])
                            cand_v1_y.append(f_right['ny'])
                    elif fs_sorted:
                        f1 = max(fs_sorted, key=lambda x: x['area'])
                        cand_v1_x.append(f1['nx'])
                        cand_v1_y.append(f1['ny'])

            def get_avg(vals): return statistics.mean(vals) if vals else 0.5
            
            if is_dual_track and not cand_v2_x: is_dual_track = False
                
            if cand_v1_x: center_v1 = (get_avg(cand_v1_x), get_avg(cand_v1_y))
            
            if is_dual_track:
                if cand_v2_x: center_v2 = (get_avg(cand_v2_x), get_avg(cand_v2_y))
                else: 
                     if last_center_v2 != (0.5, 0.5): center_v2 = last_center_v2
                     else: center_v2 = (center_v1[0] + 0.25, center_v1[1])
            
            cuts_v1.append({"start": start_f, "end": end_f, "center": center_v1})
            if is_dual_track:
                cuts_v2.append({"start": start_f, "end": end_f, "center": center_v2})
                last_center_v2 = center_v2
                is_last_dual = True
            else:
                is_last_dual = False
            
            last_center_v1 = center_v1
            current_frame = end_f
            
        if current_frame < duration_frames:
            cuts_v1.append({"start": current_frame, "end": duration_frames, "center": last_center_v1})
            
    else:
        cuts_v1.append({"start": 0, "end": duration_frames, "center": (0.5, 0.5)})

    # --- VIDEO TRACK GENERATION (SPLIT) ---
    dual_starts = set(c['start'] for c in cuts_v2)
    
    def make_video_track_split(cuts_list, track_type="main"):
        items = ""
        for cut in cuts_list:
            seg_start, seg_end = cut['start'], cut['end']
            nx, ny = cut['center']
            
            if seg_end - seg_start <= 0: continue
            is_dual = (seg_start in dual_starts)
            
            src_w = float(source_width)
            src_h = float(source_height)
            target_w = float(width)
            target_h = float(height)
            
            pane_h = target_h / 2.0 if (is_dual or track_type == "secondary") else target_h
            
            scale_w = target_w / src_w
            scale_h = pane_h / src_h
            s_val = max(scale_w, scale_h)
            final_scale = s_val * 100.0
            
            # Position Logic
            pos_h = 0.5
            if track_type == "secondary": pos_v = 0.25
            elif track_type == "main" and is_dual: pos_v = 0.75
            else: pos_v = 0.5
            
            clip_sw = src_w * s_val
            clip_sh = src_h * s_val
            
            margin_x = (clip_sw - target_w) / 2.0
            margin_y = (clip_sh - pane_h) / 2.0
            
            face_off_x = (nx - 0.5) * src_w * s_val
            face_off_y = (ny - 0.5) * src_h * s_val
            
            shift_x = -face_off_x
            shift_y = -face_off_y
            shift_x = max(-margin_x, min(margin_x, shift_x))
            shift_y = max(-margin_y, min(margin_y, shift_y))
            
            pos_h += shift_x / target_w
            pos_v += shift_y / target_h
            
            seg_id = f"clipitem-video-{xc.get_uid()}"
            
            basic_motion = f"""<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype><parameter authoringApp="PremierePro"><parameterid>scale</parameterid><name>Scale</name><value>{final_scale:.2f}</value></parameter><parameter authoringApp="PremierePro"><parameterid>center</parameterid><name>Position</name><value><horiz>{pos_h:.5f}</horiz><vert>{pos_v:.5f}</vert></value></parameter></effect></filter>"""
            
            crop_xml = ""
            if (is_dual or track_type == "secondary") and clip_sh > pane_h + 1.0:
                overflow_top = (clip_sh / 2.0) + shift_y - (pane_h / 2.0)
                overflow_bot = (clip_sh / 2.0) - shift_y - (pane_h / 2.0)
                overflow_top = max(0.0, overflow_top)
                overflow_bot = max(0.0, overflow_bot)
                
                pct_top = (overflow_top / clip_sh) * 100.0
                pct_bottom = (overflow_bot / clip_sh) * 100.0
                pct_top = max(0.0, min(100.0, pct_top))
                pct_bottom = max(0.0, min(100.0, pct_bottom))
                
                if pct_top > 0.01 or pct_bottom > 0.01:
                    crop_params = ""
                    if pct_top > 0.01: crop_params += f"""<parameter authoringApp="PremierePro"><parameterid>top</parameterid><name>Top</name><value>{pct_top:.2f}</value></parameter>"""
                    if pct_bottom > 0.01: crop_params += f"""<parameter authoringApp="PremierePro"><parameterid>bottom</parameterid><name>Bottom</name><value>{pct_bottom:.2f}</value></parameter>"""
                    crop_xml = f"""<filter><effect><name>Crop</name><effectid>crop</effectid><effectcategory>transform</effectcategory><effecttype>video</effecttype><mediatype>video</mediatype>{crop_params}</effect></filter>"""
                    
            safe_video_name = escape(os.path.basename(video_path))
            items += f"""<clipitem id="{seg_id}"><name>{safe_video_name}</name><duration>{duration_frames}</duration><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><start>{seg_start}</start><end>{seg_end}</end><in>{seg_start}</in><out>{seg_end}</out>{xc.get_file_block(video_file_id, video_path, timebase, duration_frames, source_width, source_height)}{basic_motion}{crop_xml}</clipitem>"""
        return f"<track>{items}</track>"
        
    track_v1_xml = make_video_track_split(cuts_v1, "main")
    track_v2_xml = make_video_track_split(cuts_v2, "secondary")
    
    # Overlay Track
    track_overlay_xml = xc.generate_overlay_track_xml(overlay_segments, fps_float, timebase, width, height, xc.get_uid)
    
    # Subtitle Track
    track_subtitle_xml = xc.generate_subtitle_track_xml(subtitle_data, subtitle_config, timebase, width, height, xc.get_uid, face_mode="2")
    
    # Audio Track (Simple Center Pan)
    track_audio_xml = f"""<track><clipitem id="clipitem-audio-{xc.get_uid()}"><name>{escape(os.path.basename(video_path))}</name><duration>{duration_frames}</duration><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><start>0</start><end>{duration_frames}</end><in>0</in><out>{duration_frames}</out>{xc.get_file_block(audio_file_id, video_path, timebase, duration_frames, source_width, source_height, is_audio_only=False)}<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack><filter><effect><name>Audio Pan</name><effectid>audiopan</effectid><effectcategory>audio</effectcategory><effecttype>audio</effecttype><mediatype>audio</mediatype><parameter authoringApp="PremierePro"><parameterid>pan</parameterid><name>Pan</name><valuemin>-100</valuemin><valuemax>100</valuemax><value>0</value></parameter></effect></filter></clipitem></track>"""

    # Construct XML
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
<sequence id="{sequence_uuid}">
    <uuid>{sequence_uuid}</uuid>
    <name>{escape(project_name)} (2-Face)</name>
    <duration>{duration_frames}</duration>
    <rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate>
    <media>
        <video>
            <format><samplecharacteristics><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><width>{width}</width><height>{height}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></format>
            {track_v1_xml}
            {track_v2_xml}
            {track_overlay_xml}
            {track_subtitle_xml}
        </video>
        <audio>
            <numOutputChannels>2</numOutputChannels>
            <format><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics></format>
            {track_audio_xml}
        </audio>
    </media>
</sequence>
</xmeml>"""
    return xml_content
