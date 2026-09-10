import os
import uuid
import statistics
from xml.sax.saxutils import escape

# Import common utilities
from . import xml_common as xc

def generate_xml_1face(project_name, video_path, overlay_segments, duration_frames, width=1080, height=1920, timebase=30, video_file_id=None, audio_file_id=None, scale_value=100.0, face_data=None, source_width=1920, source_height=1080, subtitle_data=None, subtitle_config=None, face_mode="1"):
    """
    Generates Premiere Pro XML for ONE-FACE scenarios (Simple Center + Zoom strategy).
    """
    
    if not video_file_id: video_file_id = f"file-video-{xc.get_uid()}"
    if not audio_file_id: audio_file_id = f"file-audio-{xc.get_uid()}"
    sequence_uuid = str(uuid.uuid4())
    
    # Process Face Data (Simplified for single track)
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

        print(f"[DEBUG 1FACE] Iniciando processamento de {len(face_data)} entradas de face_data.")
        count_processed = 0
        for entry in face_data:
            f_idx = entry.get('frame')
            faces = entry.get('faces', [])
            
            # Debug para as primeiras entradas para ver a estrutura
            if count_processed < 3:
                print(f"[DEBUG 1FACE] Entry {count_processed}: Frame={f_idx}, Faces={len(faces)}")
            
            if not faces: continue
            
            processed_faces = []
            for f in faces:
                cx = (f[0] + f[2]) / 2.0
                cy = (f[1] + f[3]) / 2.0
                area = (f[2]-f[0]) * (f[3]-f[1])
                nx = cx / max(1.0, float(coords_w))
                ny = cy / max(1.0, float(coords_h))
                
                processed_faces.append({'nx': nx, 'ny': ny, 'area': area})
            
            # Garantir que f_idx é inteiro
            try:
                f_int = int(f_idx)
                faces_per_frame[f_int] = processed_faces
                count_processed += 1
            except:
                pass
            
    # --- DEBUG DATA LOADING ---
    print(f"[DEBUG 1FACE] Carregados {len(faces_per_frame)} quadros com dados de face no dicionário.")
    if len(faces_per_frame) > 0:
        sample_keys = sorted(list(faces_per_frame.keys()))
        print(f"[DEBUG 1FACE] Primeiros 5 Frames: {sample_keys[:5]}")
        print(f"[DEBUG 1FACE] Exemplo Frame 0: {faces_per_frame.get(0, 'N/A')}")
        print(f"[DEBUG 1FACE] Exemplo Frame 10: {faces_per_frame.get(10, 'N/A')}")
        print(f"[DEBUG 1FACE] Exemplo Frame 50: {faces_per_frame.get(50, 'N/A')}")
        
    else:
        print("[DEBUG 1FACE] AVISO: faces_per_frame ESTÁ VAZIO! Verifique se 'frame' existe no JSON.")
    # --------------------------
            
    # Segmentation for Single Track
    cuts_v1 = []
    fps_float = float(timebase)
    
    if overlay_segments:
        current_frame = 0
        last_center = (0.5, 0.5)
        
        sorted_segs = sorted(overlay_segments, key=lambda x: x['start'])
        
        for idx, seg in enumerate(sorted_segs):
            start_f = int(seg['start'] * fps_float)
            end_f = int(seg['end'] * fps_float)
            
            # Gap
            if start_f > current_frame:
                cuts_v1.append({"start": current_frame, "end": start_f, "center": last_center})
            
            # Analyze faces for this segment
            cand_x, cand_y = [], []
            for f_idx in range(start_f, end_f):
                if f_idx in faces_per_frame:
                    fs = faces_per_frame[f_idx]
                    if fs:
                        # Pick biggest face only
                        best = max(fs, key=lambda x: x['area'])
                        cand_x.append(best['nx'])
                        cand_y.append(best['ny'])
            
            center = last_center
            if cand_x:
                avg_x = statistics.mean(cand_x)
                avg_y = statistics.mean(cand_y)
                center = (avg_x, avg_y)
            
            cuts_v1.append({"start": start_f, "end": end_f, "center": center})
            last_center = center
            current_frame = end_f
            
        if current_frame < duration_frames:
            cuts_v1.append({"start": current_frame, "end": duration_frames, "center": last_center})
    else:
        cuts_v1.append({"start": 0, "end": duration_frames, "center": (0.5, 0.5)})

    # --- VIDEO TRACK GENERATION (SIMPLE) ---
    def make_video_track_simple(cuts_list):
        items = ""
        last_valid_center = None
        
        for cut in cuts_list:
            seg_start, seg_end = cut['start'], cut['end']
            nx, ny = cut['center']
            
            if seg_end - seg_start <= 0: continue
            
            # Static Mode (Average Center for Segment)
            # This is more robust than keyframing which can fail if XML syntax is slightly off
            
            # Calculate Average Center for this segment
            cand_x, cand_y = [], []
            has_new_data = False
            
            for f_idx in range(seg_start, seg_end):
                if f_idx in faces_per_frame and faces_per_frame[f_idx]:
                    best = max(faces_per_frame[f_idx], key=lambda x: x['area'])
                    cand_x.append(best['nx'])
                    cand_y.append(best['ny'])
            
            nx, ny = (0.5, 0.5)
            origin_type = "[PADRAO]"
            
            if cand_x:
                nx = statistics.mean(cand_x)
                ny = statistics.mean(cand_y)
                # Update global last valid
                last_valid_center = (nx, ny)
                has_new_data = True
                origin_type = "[DETECTADO]"
            elif last_valid_center:
                # Fallback to last known good face position to avoid jumping to center
                nx, ny = last_valid_center
                origin_type = "[PERSISTIDO]"
            elif cut.get('center'):
                 nx, ny = cut['center']

            # Scale Calculation
            src_w = float(source_width)
            src_h = float(source_height)
            target_w = float(width)
            target_h = float(height)
            
            scale_w = target_w / src_w
            scale_h = target_h / src_h
            s_val = max(scale_w, scale_h) # Base 'Cover' scale

            # Apply User Scaling Preference
            user_scale_factor = float(scale_value) / 100.0
            s_val = s_val * user_scale_factor
            
            final_scale = s_val * 100.0 
            
            # Position Logic (Normalized for Basic Motion)
            clip_sw = src_w * s_val
            
            # Offset of face from center of scaled image
            face_off_x = (nx - 0.5) * clip_sw
            shift_x = -face_off_x
            
            # Smart Margin Clamp (prevent black bars)
            margin_x = (clip_sw - target_w) / 2.0
            if margin_x > 0:
                shift_x = max(-margin_x, min(margin_x, shift_x))
            
            # --- OLD WORKING MATH ---
            # 1. Face Offset from Clip Center (in Source Pixels)
            off_x_src = (nx - 0.5) * src_w
            off_y_src = (ny - 0.5) * src_h
            
            # 2. Face Offset in Screen Pixels (after Scale)
            off_x_seq = off_x_src * s_val
            off_y_seq = off_y_src * s_val
            
            # 3. Target Screen Position (Center of Sequence)
            target_screen_x = 0.5 * target_w
            target_screen_y = 0.5 * target_h
            
            # 4. Required Clip Center Position
            req_center_x = target_screen_x - off_x_seq
            req_center_y = target_screen_y - off_y_seq
            
            # 5. Normalize for XML (-0.5 to 0.5)
            pos_h = (req_center_x / target_w) - 0.5
            pos_v = (req_center_y / target_h) - 0.5
            
            seg_id = f"clipitem-video-{xc.get_uid()}"
            safe_video_name = escape(os.path.basename(video_path))
            
            # Filtro 'Basic Motion' Clássico (Funcional)
            basic_motion = f"""<filter>
                    <effect>
                        <name>Basic Motion</name>
                        <effectid>basic</effectid>
                        <effectcategory>motion</effectcategory>
                        <effecttype>motion</effecttype>
                        <mediatype>video</mediatype>
                        <parameter authoringApp="PremierePro">
                            <parameterid>scale</parameterid>
                            <name>Scale</name>
                            <value>{final_scale:.2f}</value>
                        </parameter>
                        <parameter authoringApp="PremierePro">
                            <parameterid>center</parameterid>
                            <name>Center</name>
                            <value>
                                <horiz>{pos_h:.5f}</horiz>
                                <vert>{pos_v:.5f}</vert>
                            </value>
                        </parameter>
                    </effect>
                </filter>"""
            
            # --- DEBUG LOGGING (PORTUGUESE) ---
            print(f"[DEBUG XML 1FACE] Segmento: {seg_start}-{seg_end}")
            print(f"  > Centro Médio (nx, ny): ({nx:.4f}, {ny:.4f}) {origin_type}")
            print(f"  > Escala Final: {final_scale:.2f}% (User Scale: {scale_value}%)")
            print(f"  > Posição XML (H, V): ({pos_h:.5f}, {pos_v:.5f})")
            print("---------------------------------------------------")
            # ----------------------------------
            
            items += f"""<clipitem id="{seg_id}"><name>{safe_video_name}</name><duration>{duration_frames}</duration><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><start>{seg_start}</start><end>{seg_end}</end><in>{seg_start}</in><out>{seg_end}</out>{xc.get_file_block(video_file_id, video_path, timebase, duration_frames, source_width, source_height)}{basic_motion}</clipitem>"""
        return f"<track>{items}</track>"
        
    track_v1_xml = make_video_track_simple(cuts_v1)
    
    # Overlay Track
    track_overlay_xml = xc.generate_overlay_track_xml(overlay_segments, fps_float, timebase, width, height, xc.get_uid)
    
    # Subtitle Track
    # Ensure default font size if not specified (Fix for small font)
    if subtitle_config is None:
        subtitle_config = {}
    if 'font_size' not in subtitle_config:
        subtitle_config['font_size'] = 110

    track_subtitle_xml = xc.generate_subtitle_track_xml(subtitle_data, subtitle_config, timebase, width, height, xc.get_uid, face_mode="1")
    
    # Audio Track (Simple Center Pan)
    track_audio_xml = f"""<track><clipitem id="clipitem-audio-{xc.get_uid()}"><name>{escape(os.path.basename(video_path))}</name><duration>{duration_frames}</duration><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><start>0</start><end>{duration_frames}</end><in>0</in><out>{duration_frames}</out>{xc.get_file_block(audio_file_id, video_path, timebase, duration_frames, source_width, source_height, is_audio_only=False)}<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack><filter><effect><name>Audio Pan</name><effectid>audiopan</effectid><effectcategory>audio</effectcategory><effecttype>audio</effecttype><mediatype>audio</mediatype><parameter authoringApp="PremierePro"><parameterid>pan</parameterid><name>Pan</name><valuemin>-100</valuemin><valuemax>100</valuemax><value>0</value></parameter></effect></filter></clipitem></track>"""

    # Construct XML
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
<sequence id="{sequence_uuid}">
    <uuid>{sequence_uuid}</uuid>
    <name>{escape(project_name)} (1-Face)</name>
    <duration>{duration_frames}</duration>
    <rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate>
    <media>
        <video>
            <format><samplecharacteristics><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><width>{width}</width><height>{height}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></format>
            {track_v1_xml}
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
