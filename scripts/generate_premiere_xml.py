import os
import uuid

def create_premiere_xml(project_name, video_path, overlay_path, duration_frames, width=1080, height=1920, timebase=30, face_data=None, source_width=1920, source_height=1080):
    """
    Generates a Premiere Pro XML (xmeml version 4) compliant with vertical restrictions.
    video_path: Path to the main video (Track 1)
    overlay_path: Path to the transparent overlay video (Track 2), can be None.
    face_data: List of dicts [{"frame": i, "faces": [[x1,y1,x2,y2]]}, ...]
    source_width/height: Resolution of the source video for coordinate normalization.
    """
    
    # Generate unique IDs
    sequence_uuid = str(uuid.uuid4())
    video_clip_id = "clipitem-video-1"
    overlay_clip_id = "clipitem-overlay-1" 
    audio_clip_id = "clipitem-audio-1"
    
    video_file_id = f"file-video-{os.path.basename(video_path)}"
    audio_file_id = f"file-audio-{os.path.basename(video_path)}"
    overlay_file_id = f"file-overlay-{os.path.basename(overlay_path)}" if overlay_path else None
    
    # Scale Calculation
    # We want to fill the Vertical Screen (Height 1920) with the Source Height (source_height)
    # Scale = Target / Source * 100
    scale_value = (height / source_height) * 100.0
    # ensure it fills width too (if source is super tall? unlikely 16:9)
    if (source_width * (scale_value/100)) < width:
         scale_value = (width / source_width) * 100.0
         
    # Keyframe Generation for Center/Position (Absolute Pixels)
    center_keyframes = ""
    default_horiz = width / 2.0
    default_vert = height / 2.0
    
    if face_data:
        kf_blocks = []
        sorted_data = sorted(face_data, key=lambda x: x['frame'])
        
        s_factor = scale_value / 100.0
        src_cx = source_width / 2.0
        src_cy = source_height / 2.0
        
        last_h = default_horiz
        last_v = default_vert
        
        for entry in sorted_data:
            frame_idx = entry['frame']
            if frame_idx >= duration_frames: break 
            
            # Simple Logic: Focus on the "First" face
            faces = entry.get('faces', [])
            
            current_h = last_h
            current_v = last_v
            
            if faces and len(faces) > 0:
                f = faces[0]
                if len(f) == 4:
                    cx = (f[0] + f[2]) / 2.0
                    cy = (f[1] + f[3]) / 2.0
                    
                    off_x = cx - src_cx
                    off_y = cy - src_cy
                    
                    # Target = CenterSeq - (OffsetSrc * Scale)
                    target_h = default_horiz - (off_x * s_factor)
                    target_v = default_vert - (off_y * s_factor)
                    
                    # CLAMP SAFEGUARDS (Keep center within logical bounds)
                    # Don't let the anchor point go way off screen. 
                    # The video needs to cover the screen (1080x1920)
                    # At scale 88% of 4K, video is ~3400px wide.
                    # We can move it quite a bit.
                    # Limit target center to be within -1000 to +2000 roughly? 
                    # Let's clamp to strict +/- 2000 of center to avoid overflow errors
                    target_h = max(-3000, min(4000, target_h))
                    target_v = max(-3000, min(5000, target_v))
                    
                    current_h = target_h
                    current_v = target_v
                    last_h = current_h
                    last_v = current_v

            kf_blocks.append(f"""
                <keyframe>
                    <when>{frame_idx}</when>
                    <value>
                        <horiz>{current_h:.2f}</horiz>
                        <vert>{current_v:.2f}</vert>
                    </value>
                </keyframe>""")
        
        center_keyframes = "\n".join(kf_blocks)

    timecode_block = f"""
            <timecode>
                <rate>
                    <timebase>{timebase}</timebase>
                    <ntsc>FALSE</ntsc>
                </rate>
                <string>00:00:00:00</string>
                <frame>0</frame>
                <displayformat>NDF</displayformat>
            </timecode>"""

    def get_file_block(fid, fpath, is_audio_only=False):
        # File defines Source properties
        width_f = source_width
        height_f = source_height
        
        audio_blk = """
                <audio>
                  <samplecharacteristics>
                    <depth>16</depth>
                    <samplerate>48000</samplerate>
                  </samplecharacteristics>
                  <channelcount>2</channelcount>
                </audio>""" if not is_audio_only else ""
        
        return f"""
            <file id="{fid}">
              <name>{os.path.basename(fpath)}</name>
              <pathurl>{fpath}</pathurl>
              <rate>
                <timebase>{timebase}</timebase>
                <ntsc>FALSE</ntsc>
              </rate>
              <duration>{duration_frames}</duration>
              <timecode>
                <rate>
                    <timebase>{timebase}</timebase>
                    <ntsc>FALSE</ntsc>
                </rate>
                <string>00:00:00:00</string>
                <frame>0</frame>
                <displayformat>NDF</displayformat>
              </timecode>
              <media>
                <video>
                  <samplecharacteristics>
                    <width>{width_f}</width>
                    <height>{height_f}</height>
                    <alpha>straight</alpha> 
                  </samplecharacteristics>
                </video>
                {audio_blk}
              </media>
            </file>"""

    track_overlay_block = ""
    if overlay_path:
        track_overlay_block = f"""
        <track>
          <clipitem id="{overlay_clip_id}">
            <name>{os.path.basename(overlay_path)}</name>
            <duration>{duration_frames}</duration>
            <rate>
              <timebase>{timebase}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
            <start>0</start>
            <end>{duration_frames}</end>
            {get_file_block(overlay_file_id, overlay_path)}
            <compositemode>normal</compositemode> 
          </clipitem>
        </track>
        """
    else:
        track_overlay_block = "<track></track>"

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<xmeml version="4">
  <sequence id="{sequence_uuid}">
    <name>{project_name}</name>
    <duration>{duration_frames}</duration>
    <rate>
      <timebase>{timebase}</timebase>
      <ntsc>FALSE</ntsc>
    </rate>
    {timecode_block}
    <media>
      <video>
        <format>
          <samplecharacteristics>
            <rate>
              <timebase>{timebase}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
            <width>{width}</width>
            <height>{height}</height>
            <pixelaspectratio>square</pixelaspectratio>
          </samplecharacteristics>
        </format>
        
        <track>
          <clipitem id="{video_clip_id}">
            <name>{os.path.basename(video_path)}</name>
            <duration>{duration_frames}</duration>
            <rate>
              <timebase>{timebase}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
            <start>0</start>
            <end>{duration_frames}</end>
            {get_file_block(video_file_id, video_path)}
            <filter>
              <effect>
                <name>Basic Motion</name>
                <effectid>basic</effectid>
                <effectcategory>motion</effectcategory>
                <effecttype>motion</effecttype>
                <mediatype>video</mediatype>
                <parameter authoringApp="PremierePro">
                  <parameterid>scale</parameterid>
                  <name>Scale</name>
                  <valuemin>0</valuemin>
                  <valuemax>1000</valuemax>
                  <value>{scale_value}</value>
                </parameter>
                <parameter authoringApp="PremierePro">
                  <parameterid>center</parameterid>
                  <name>Center</name>
                  <value>
                    <horiz>{default_horiz}</horiz>
                    <vert>{default_vert}</vert>
                  </value>
                  {center_keyframes}
                </parameter>
              </effect>
            </filter>
          </clipitem>
        </track>
        
        {track_overlay_block}
        
      </video>
      <audio>
        <track>
          <clipitem id="{audio_clip_id}">
             <name>{os.path.basename(video_path)}</name>
             <duration>{duration_frames}</duration>
             <rate>
               <timebase>{timebase}</timebase>
               <ntsc>FALSE</ntsc>
             </rate>
             <start>0</start>
             <end>{duration_frames}</end>
             {get_file_block(audio_file_id, video_path)}
             <sourcetrack>
               <mediatype>audio</mediatype>
               <trackindex>1</trackindex>
             </sourcetrack>
             <link>
               <linkclipref>{video_clip_id}</linkclipref>
               <mediatype>video</mediatype>
               <trackindex>1</trackindex>
               <clipindex>1</clipindex>
             </link>
             <link>
               <linkclipref>{audio_clip_id}</linkclipref>
               <mediatype>audio</mediatype>
               <trackindex>1</trackindex>
               <clipindex>1</clipindex>
             </link>
          </clipitem>
        </track>
      </audio>
    </media>
  </sequence>
</xmeml>
"""
    return xml_content

if __name__ == "__main__":
    pass
