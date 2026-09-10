from .xml_1face import generate_xml_1face
from .xml_2face import generate_xml_2face

def create_premiere_xml(project_name, video_path, overlay_segments, duration_frames, width=1080, height=1920, timebase=30, video_file_id=None, audio_file_id=None, scale_value=100.0, face_data=None, source_width=1920, source_height=1080, subtitle_data=None, subtitle_config=None, face_mode="1"):
    """
    Dispatcher for Premiere Pro XML Generation.
    Delegates to specialized modules based on face_mode.
    """
    
    print(f"[Gerador XML] Despachando com base no Modo de Face: {face_mode}")
    
    # Ensure inputs are correct types
    source_width = float(source_width)
    source_height = float(source_height)
    width = float(width)
    height = float(height)
    
    if str(face_mode) == "2":
        return generate_xml_2face(
            project_name=project_name,
            video_path=video_path,
            overlay_segments=overlay_segments,
            duration_frames=duration_frames,
            width=width,
            height=height,
            timebase=timebase,
            video_file_id=video_file_id,
            audio_file_id=audio_file_id,
            scale_value=scale_value,
            face_data=face_data,
            source_width=source_width,
            source_height=source_height,
            subtitle_data=subtitle_data,
            subtitle_config=subtitle_config,
            face_mode=face_mode
        )
    else:
        # Default to 1-Face Mode
        return generate_xml_1face(
            project_name=project_name,
            video_path=video_path,
            overlay_segments=overlay_segments,
            duration_frames=duration_frames,
            width=width,
            height=height,
            timebase=timebase,
            video_file_id=video_file_id,
            audio_file_id=audio_file_id,
            scale_value=scale_value,
            face_data=face_data,
            source_width=source_width,
            source_height=source_height,
            subtitle_data=subtitle_data,
            subtitle_config=subtitle_config,
            face_mode=face_mode
        )
