import os
import uuid
import struct
import base64
import json
from xml.sax.saxutils import escape

def get_uid(): 
    return str(uuid.uuid4())[:12]

def hex_to_decimal_color(hex_color):
    """Convert #RRGGBB to decimal RGB for Premiere (e.g. #FFFFFF -> 16777215)"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        return int(hex_color, 16)
    return 16777215  # white

def get_file_block(fid, fpath, timebase, duration_frames, width, height, is_audio_only=False):
   audio_blk = "" if is_audio_only else "<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics><channelcount>2</channelcount></audio>"
   width_f = int(width)
   height_f = int(height)
   # Escape XML special chars in path and name
   safe_name = escape(os.path.basename(fpath))
   safe_path = escape(fpath)
   return f"""<file id="{fid}"><name>{safe_name}</name><pathurl>{safe_path}</pathurl><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><duration>{duration_frames}</duration><media><video><samplecharacteristics><width>{width_f}</width><height>{height_f}</height><alpha>straight</alpha></samplecharacteristics></video>{audio_blk}</media></file>"""

def create_premiere_graphics_payload(text, font_name="Arial", font_size=84, fill_color_hex="#FFFFFF", 
                                    stroke_visible=False, stroke_color_hex="#000000", stroke_width=2,
                                    shadow_visible=False, shadow_color_hex="#000000", shadow_offset=5, shadow_opacity=100,
                                    alignment=1, highlights=None,
                                    back_visible=False, back_color_hex="#000000", back_opacity=75, back_size=0, back_radius=10,
                                    fill_over_stroke=True,
                                    faux_bold=False, faux_italic=False, all_caps=False, underline=False,
                                    underline_on_highlight=False, ghost_mode=False):
    """
    Create Premiere Pro Graphics Source Text payload (Base64 UTF-16LE)
    highlights: List of dicts: {'start': int, 'end': int, 'color': int, 'size': int}
    """
    # Sanitize font name to prevent "[Arial]" issue if user/preset includes brackets
    raw_font = str(font_name)
    font_name = raw_font.strip().replace('[', '').replace(']', '')
    
    # Map common font names to their PostScript names that Premiere expects
    font_name_map = {
        "Arial": "ArialMT",
        "Arial Bold": "Arial-BoldMT",
        "Arial Italic": "Arial-ItalicMT",
        "Arial Bold Italic": "Arial-BoldItalicMT",
        "Times New Roman": "TimesNewRomanPSMT",
        "Times New Roman Bold": "TimesNewRomanPS-BoldMT",
        "Times New Roman Italic": "TimesNewRomanPS-ItalicMT",
        "Courier New": "CourierNewPSMT",
        "Helvetica": "Helvetica",
        "Verdana": "Verdana",
        "Georgia": "Georgia",
        "Comic Sans MS": "ComicSansMS",
        "Trebuchet MS": "TrebuchetMS",
        "Impact": "Impact",
        "Calibri": "Calibri",
        "Consolas": "Consolas",
        "Cambria": "Cambria",
        "Montserrat": "Montserrat-Regular",
        "Montserrat Regular": "Montserrat-Regular",
        "Montserrat Bold": "Montserrat-Bold",
        "Montserrat ExtraBold": "Montserrat-ExtraBold",
        "Montserrat Black": "Montserrat-Black",
        "Montserrat Medium": "Montserrat-Medium",
        "Montserrat SemiBold": "Montserrat-SemiBold",
        "Open Sans": "OpenSans-Regular",
        "Open Sans Bold": "OpenSans-Bold",
        "Roboto": "Roboto-Regular",
        "Roboto Bold": "Roboto-Bold",
    }
    
    # Apply font mapping (case-insensitive)
    for display_name, ps_name in font_name_map.items():
        if font_name.lower() == display_name.lower():
            font_name = ps_name
            break
    
    fill_color_dec = hex_to_decimal_color(fill_color_hex)
    stroke_color_dec = hex_to_decimal_color(stroke_color_hex)
    shadow_color_dec = hex_to_decimal_color(shadow_color_hex)
    back_color_dec = hex_to_decimal_color(back_color_hex)
    
    # --- Build Param Values ---
    fill_param_values = [[0, fill_color_dec]]
    size_param_values = [[0, font_size]]
    
    base_under = underline
    if underline_on_highlight: base_under = False
    under_param_values = [[0, base_under]]
    
    base_visible = True
    if ghost_mode: base_visible = False
    visible_param_values = [[0, base_visible]]
    
    if highlights:
        fill_param_values = []
        size_param_values = []
        under_param_values = []
        visible_param_values = []
        
        # Sanitize: Trim whitespace from highlight ranges
        clean_highlights = []
        for h in highlights:
            s, e = h['start'], h['end']
            s = max(0, min(len(text), s))
            e = max(0, min(len(text), e))
            if s >= e: continue
            
            sub = text[s:e]
            l_trim = len(sub) - len(sub.lstrip())
            r_trim = len(sub) - len(sub.rstrip())
            
            new_s = s + l_trim
            new_e = e - r_trim
            
            if new_e > new_s:
                nh = h.copy()
                nh['start'] = new_s
                nh['end'] = new_e
                clean_highlights.append(nh)
        
        sorted_highlights = sorted(clean_highlights, key=lambda x: x['start'])
        current_idx = 0
        
        for h in sorted_highlights:
            start = h['start']
            end = h['end']
            color = h.get('color', fill_color_dec)
            size = h.get('size', font_size)
            
            # Fill gap with base style
            if start > current_idx:
                fill_param_values.append([current_idx, fill_color_dec])
                size_param_values.append([current_idx, font_size])
                under_param_values.append([current_idx, base_under])
                visible_param_values.append([current_idx, base_visible])
            
            # Add highlight style
            fill_param_values.append([start, color])
            size_param_values.append([start, size])
            hl_under = True if underline_on_highlight else underline
            under_param_values.append([start, hl_under])
            visible_param_values.append([start, True])
            
            current_idx = end
            
        # Final segment
        if current_idx < len(text):
            fill_param_values.append([current_idx, fill_color_dec])
            size_param_values.append([current_idx, font_size])
            under_param_values.append([current_idx, base_under])
            visible_param_values.append([current_idx, base_visible])
        
        # Ensure starts at 0
        if not fill_param_values or fill_param_values[0][0] != 0:
            fill_param_values.insert(0, [0, fill_color_dec])
            if size_param_values and size_param_values[0][0] != 0: size_param_values.insert(0, [0, font_size])
            if under_param_values and under_param_values[0][0] != 0: under_param_values.insert(0, [0, base_under])
            if visible_param_values and visible_param_values[0][0] != 0: visible_param_values.insert(0, [0, base_visible])

    # Fallback if empty lists
    if not fill_param_values:
        fill_param_values = [[0, fill_color_dec]]
        size_param_values = [[0, font_size]]
        under_param_values = [[0, base_under]]
        visible_param_values = [[0, base_visible]]

    data = {
        "mTextParam": {
            "mAlignment": alignment, # 0=Left, 1=Center, 2=Right
            "mBackFillColor": back_color_dec,
            "mBackFillOpacity": float(back_opacity),
            "mBackFillSize": float(back_size),
            "mBackFillVisible": back_visible,
            "mBackFillCornerRadius": float(back_radius),
            "mDefaultRun": [],
            "mHeight": 0,
            "mHindiDigits": False,
            "mIndic": False,
            "mIsVerticalText": False,
            "mLeading": 0,
            "mLigatures": False,
            "mRTL": False,
            "mShadowAngle": 135,
            "mShadowBlur": 0,
            "mShadowColor": shadow_color_dec,
            "mShadowOffset": int(shadow_offset),
            "mShadowOpacity": int(shadow_opacity),
            "mShadowVisible": shadow_visible,
            "mStyleSheet": {
                "mBaselineShift": {"mParamValues": [[0, 0]]},
                "mCapsOption": {"mParamValues": [[0, 1 if all_caps else 0]]},
                "mFauxBold": {"mParamValues": [[0, faux_bold]]},
                "mFauxItalic": {"mParamValues": [[0, faux_italic]]},
                "mUnderline": {"mParamValues": under_param_values},
                "mFillColor": {"mParamValues": fill_param_values},
                "mFillOverStroke": {"mParamValues": [[0, fill_over_stroke]]},
                "mFillVisible": {"mParamValues": visible_param_values},
                "mFontName": {"mParamValues": [[0, font_name]]},
                "mFontSize": {"mParamValues": size_param_values},
                "mKerning": {"mParamValues": [[0, 0]]},
                "mStrokeColor": {"mParamValues": [[0, stroke_color_dec]]},
                "mStrokeVisible": {"mParamValues": visible_param_values if stroke_visible else [[0, False]]},
                "mStrokeWidth": {"mParamValues": [[0, stroke_width]]},
                "mText": text,
                "mTracking": {"mParamValues": [[0, 0]]},
                "mTsumi": {"mParamValues": [[0, 0]]}
            },
            "mTabWidth": 400,
            "mWidth": 0
        },
        "mUseLegacyTextBox": False,
        "mVersion": 1,
        "mCreator": "ViralCutter XML Generator"
    }
    
    json_str = json.dumps(data, separators=(',', ':'))
    utf16_bytes = json_str.encode('utf-16le')
    size = len(utf16_bytes)
    header = struct.pack('<Q', size)
    
    return base64.b64encode(header + utf16_bytes).decode('ascii')

def generate_overlay_track_xml(overlay_segments, fps_float, timebase, width, height, get_uid_func):
    track_overlay_block = ""
    if overlay_segments:
        overlay_clips = ""
        for seg in overlay_segments:
            if not seg.get('path'): continue 
            
            start_f = int(seg['start'] * fps_float)
            end_f = int(seg['end'] * fps_float)
            clip_dur = end_f - start_f
            if clip_dur <= 0: continue
            
            ov_fid = f"file-ov-{seg['index']}-{get_uid_func()}"
            ov_cid = f"clip-ov-{seg['index']}-{get_uid_func()}"
            
            safe_ov_name = escape(os.path.basename(seg['path']))
            safe_ov_path = escape(seg['path'])
            
            file_blk = f"""<file id="{ov_fid}"><name>{safe_ov_name}</name><pathurl>{safe_ov_path}</pathurl><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><duration>{clip_dur}</duration><media><video><samplecharacteristics><width>{width}</width><height>{height}</height><alpha>straight</alpha></samplecharacteristics></video></media></file>"""
            overlay_clips += f"""<clipitem id="{ov_cid}"><name>{safe_ov_name}</name><duration>{clip_dur}</duration><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><start>{start_f}</start><end>{end_f}</end><in>0</in><out>{clip_dur}</out>{file_blk}<compositemode>normal</compositemode></clipitem>"""
        
        if overlay_clips:
            track_overlay_block = f"<track>{overlay_clips}</track>"
    return track_overlay_block

def generate_subtitle_track_xml(subtitle_data, subtitle_config, timebase, width, height, get_uid_func, face_mode="1"):
    if not subtitle_data: return ""
    
    subtitle_config = subtitle_config or {}
    font_name = subtitle_config.get('font', 'Arial')
    font_size = subtitle_config.get('font_size', 84)
    highlight_color = subtitle_config.get('highlight_color', '#FFFF00')
    text_color = subtitle_config.get('text_color', '#FFFFFF')
    stroke_color = subtitle_config.get('stroke_color', '#000000')
    stroke_width = subtitle_config.get('stroke_width', 2)
    shadow_color = subtitle_config.get('shadow_color', '#000000')
    shadow_offset = subtitle_config.get('shadow_offset', 4)
    shadow_opacity = subtitle_config.get('shadow_opacity', 100)
    
    is_bold = subtitle_config.get('bold', False)
    is_italic = subtitle_config.get('italic', False)
    is_caps = subtitle_config.get('all_caps', False)
    is_underline = subtitle_config.get('underline', False)
    
    stroke_visible = subtitle_config.get('stroke_visible', True)
    shadow_visible = subtitle_config.get('shadow_visible', True)
    fill_over_stroke = subtitle_config.get('fill_over_stroke', True)
    
    back_visible = subtitle_config.get('back_visible', False)
    back_color = subtitle_config.get('back_color', '#000000')
    back_opacity = subtitle_config.get('back_opacity', 75)
    back_size = subtitle_config.get('back_size', 0)
    back_radius = subtitle_config.get('back_radius', 10)
    
    align_code = subtitle_config.get('alignment', 2)
    
    # Position logic
    pos_x_norm = subtitle_config.get('pos_x_norm', 0.5)
    vert_pos_px = subtitle_config.get('vertical_position', 200)
    
    if str(face_mode) == "2":
        pos_y_norm = 0.5 # Center for split screen
    else:
        if vert_pos_px < 1.0 and vert_pos_px > 0:
            pos_y_norm = vert_pos_px
        else:
            pos_y_norm = (float(height) - float(vert_pos_px)) / float(height)
            
    position_value = f"-91445760000000000,{pos_x_norm:.6f}:{pos_y_norm:.6f},0,0,0,0,0,0,5,4,0,0,0,0"
    
    subtitle_clips = ""
    clip_counter = 0

    import re # Import re locally if needed or rely on module import if moved to top

    for s_idx, sub in enumerate(subtitle_data):
        if 'text' not in sub: continue
        
        text = sub.get('text', "").strip()
        clean_text = text
        remove_punc = subtitle_config.get('remove_punctuation', False)
        if remove_punc:
            clean_text = re.sub(r'[.,!?;:\-\(\)\[\]\"\'…]', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        if is_caps: clean_text = clean_text.upper()
        
        words_in_segment = sub.get('words', [])
        
        # Gap Filling
        if words_in_segment:
            gap_limit = subtitle_config.get('gap_limit', 0.2)
            for k_w in range(len(words_in_segment) - 1):
                cur_w = words_in_segment[k_w]
                nxt_w = words_in_segment[k_w+1]
                gap = nxt_w['start'] - cur_w['end']
                if 0 < gap < gap_limit:
                    cur_w['end'] = nxt_w['start']

        if notWords_in_segment := words_in_segment: # Assignment expression just to satisfy "if not words" check logic flow
             pass
        
        if not words_in_segment:
             # Logic for single clip fallback (omitted for brevity in this quick helper extract, but should be here)
             # Let's include the block logic since it handles 99% of cases
             pass

        # ... (Full subtitle logic is huge, I will copy it fully in the actual implementation of this helper if I had more space)
        # For now, to save context window and complexity, I will assume I can copy the block logic properly.
        # Implemented simplified version or placeholder?
        # No, I must implement it fully to work.
        
        # FULL IMPLEMENTATION OF KARAOKE LOGIC HERE
        # ... (Redacted for length in this thought block, will write full in tool call)
        
        # Wait, if I implement 100 lines of logic here, I might run out of tokens.
        # But it's necessary.
        
        start_frame = int(sub.get('start', 0) * float(timebase))
        end_frame = int(sub.get('end', 0) * float(timebase))
        dur_frame = end_frame - start_frame
        if dur_frame <= 0: continue

        # Simple non-karaoke as fallback if words missing
        if not words_in_segment:
            base64_payload = create_premiere_graphics_payload(
                text=clean_text, font_name=font_name, font_size=font_size, fill_color_hex=text_color,
                stroke_visible=stroke_visible, stroke_color_hex=stroke_color, stroke_width=stroke_width,
                shadow_visible=shadow_visible, shadow_color_hex=shadow_color, shadow_offset=shadow_offset, shadow_opacity=shadow_opacity,
                alignment=align_code, highlights=[], back_visible=back_visible, back_color_hex=back_color, back_opacity=back_opacity, back_size=back_size, back_radius=back_radius,
                fill_over_stroke=fill_over_stroke, faux_bold=is_bold, faux_italic=is_italic, all_caps=is_caps, underline=is_underline
            )
            
            clip_id = f"clipitem-subs-{clip_counter}-{get_uid_func()}"
            file_id = f"file-subs-{clip_counter}-{get_uid_func()}"
            safe_text_name = escape(clean_text[:50])
            clip_counter += 1
            
            # ... CLIP XML CONSTRUCTION (Standard) ...
            clip_xml = f'<clipitem id="{clip_id}"><masterclipid>masterclip-subs-{clip_counter}</masterclipid><name>{safe_text_name}</name><enabled>TRUE</enabled><duration>{dur_frame}</duration><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><start>{start_frame}</start><end>{end_frame}</end><in>0</in><out>{dur_frame}</out><alphatype>straight</alphatype><file id="{file_id}"><name>Graphic</name><mediaSource>GraphicAndType</mediaSource><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><timecode><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><string>00;00;00;00</string><frame>0</frame><displayformat>DF</displayformat></timecode><media><video><samplecharacteristics><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><width>{width}</width><height>{height}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></video></media></file><filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype><pproBypass>false</pproBypass><parameter authoringApp="PremierePro"><parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax><value>100</value></parameter><parameter authoringApp="PremierePro"><parameterid>rotation</parameterid><name>Rotation</name><valuemin>-8640</valuemin><valuemax>8640</valuemax><value>0</value></parameter><parameter authoringApp="PremierePro"><parameterid>center</parameterid><name>Center</name><value><horiz>0</horiz><vert>0</vert></value></parameter><parameter authoringApp="PremierePro"><parameterid>centerOffset</parameterid><name>Anchor Point</name><value><horiz>0</horiz><vert>0</vert></value></parameter><parameter authoringApp="PremierePro"><parameterid>antiflicker</parameterid><name>Anti-flicker Filter</name><valuemin>0.0</valuemin><valuemax>1.0</valuemax><value>0</value></parameter></effect></filter><filter><effect><name>{safe_text_name}</name><effectid>GraphicAndType</effectid><effectcategory>graphic</effectcategory><effecttype>filter</effecttype><mediatype>video</mediatype><pproBypass>false</pproBypass><parameter authoringApp="PremierePro"><parameterid>1</parameterid><name>Source Text</name><value>{base64_payload}</value></parameter><parameter authoringApp="PremierePro"><parameterid>2</parameterid><name>Transform</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>11</ParameterControlType><value>-91445760000000000,false,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>3</parameterid><name>Position</name><IsTimeVarying>false</IsTimeVarying><value>{position_value}</value></parameter><parameter authoringApp="PremierePro"><parameterid>4</parameterid><name>Scale</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>5</parameterid><name>Horizontal Scale</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>6</parameterid><name> </name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>4</ParameterControlType><value>-91445760000000000,true,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>7</parameterid><name>Rotation</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>3</ParameterControlType><value>-91445760000000000,0.,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>8</parameterid><name>Opacity</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>9</parameterid><name>Anchor Point</name><IsTimeVarying>false</IsTimeVarying><value>-91445760000000000,0:0,0,0,0,0,0,0,5,4,0,0,0,0</value></parameter></effect></filter></clipitem>'
            subtitle_clips += clip_xml
        else:
            # KARAOKE LOGIC RE-IMPLEMENTATION
            block_size = int(subtitle_config.get('words_per_block', 2))
            if block_size < 1: block_size = 1
            visual_blocks = [words_in_segment[i:i + block_size] for i in range(0, len(words_in_segment), block_size)]
            
            for vb_idx, block_words in enumerate(visual_blocks):
                block_text_parts = []
                for w in block_words:
                    wc = w.get('word', "")
                    if remove_punc: wc = re.sub(r'[.,!?;:\-\(\)\[\]\"\'…]', '', wc)
                    if is_caps: wc = wc.upper()
                    block_text_parts.append(wc.strip())
                block_display_text = " ".join(block_text_parts)
                
                current_block_search_idx = 0
                for w_data in block_words:
                    w_start_f = int(w_data['start'] * float(timebase))
                    w_end_f = int(w_data['end'] * float(timebase))
                    w_dur = w_end_f - w_start_f
                    if w_dur <= 0: continue
                    
                    wd_wc = w_data.get('word', "")
                    if remove_punc: wd_wc = re.sub(r'[.,!?;:\-\(\)\[\]\"\'…]', '', wd_wc)
                    if is_caps: wd_wc = wd_wc.upper()
                    wd_wc = wd_wc.strip()
                    
                    try:
                        hl_start = block_display_text.index(wd_wc, current_block_search_idx)
                        hl_end = hl_start + len(wd_wc)
                        current_block_search_idx = hl_end
                    except:
                        hl_start = 0
                        hl_end = 0

                    base64_payload = create_premiere_graphics_payload(
                        text=block_display_text, font_name=font_name, font_size=font_size, fill_color_hex=text_color,
                        stroke_visible=stroke_visible, stroke_color_hex=stroke_color, stroke_width=stroke_width,
                        shadow_visible=shadow_visible, shadow_color_hex=shadow_color, shadow_offset=shadow_offset,
                        shadow_opacity=shadow_opacity, alignment=align_code,
                        highlights=[{'start': hl_start, 'end': hl_end, 'color': hex_to_decimal_color(highlight_color)}],
                        back_visible=back_visible, back_color_hex=back_color, back_opacity=back_opacity,
                        back_size=back_size, back_radius=back_radius, fill_over_stroke=fill_over_stroke,
                        faux_bold=is_bold, faux_italic=is_italic, all_caps=is_caps, underline=is_underline, underline_on_highlight=True
                    )
                    
                    clip_id = f"clipitem-subs-{clip_counter}-{get_uid_func()}"
                    file_id = f"file-subs-{clip_counter}-{get_uid_func()}"
                    safe_text_name = escape(block_display_text[:50])
                    clip_counter += 1
                    
                    clip_xml = f'<clipitem id="{clip_id}"><masterclipid>masterclip-subs-{clip_counter}</masterclipid><name>{safe_text_name}</name><enabled>TRUE</enabled><duration>{w_dur}</duration><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><start>{w_start_f}</start><end>{w_end_f}</end><in>0</in><out>{w_dur}</out><alphatype>straight</alphatype><file id="{file_id}"><name>Graphic</name><mediaSource>GraphicAndType</mediaSource><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><timecode><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><string>00;00;00;00</string><frame>0</frame><displayformat>DF</displayformat></timecode><media><video><samplecharacteristics><rate><timebase>{timebase}</timebase><ntsc>FALSE</ntsc></rate><width>{width}</width><height>{height}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></video></media></file><filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype><pproBypass>false</pproBypass><parameter authoringApp="PremierePro"><parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax><value>100</value></parameter><parameter authoringApp="PremierePro"><parameterid>rotation</parameterid><name>Rotation</name><valuemin>-8640</valuemin><valuemax>8640</valuemax><value>0</value></parameter><parameter authoringApp="PremierePro"><parameterid>center</parameterid><name>Center</name><value><horiz>0</horiz><vert>0</vert></value></parameter><parameter authoringApp="PremierePro"><parameterid>centerOffset</parameterid><name>Anchor Point</name><value><horiz>0</horiz><vert>0</vert></value></parameter><parameter authoringApp="PremierePro"><parameterid>antiflicker</parameterid><name>Anti-flicker Filter</name><valuemin>0.0</valuemin><valuemax>1.0</valuemax><value>0</value></parameter></effect></filter><filter><effect><name>{safe_text_name}</name><effectid>GraphicAndType</effectid><effectcategory>graphic</effectcategory><effecttype>filter</effecttype><mediatype>video</mediatype><pproBypass>false</pproBypass><parameter authoringApp="PremierePro"><parameterid>1</parameterid><name>Source Text</name><value>{base64_payload}</value></parameter><parameter authoringApp="PremierePro"><parameterid>2</parameterid><name>Transform</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>11</ParameterControlType><value>-91445760000000000,false,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>3</parameterid><name>Position</name><IsTimeVarying>false</IsTimeVarying><value>{position_value}</value></parameter><parameter authoringApp="PremierePro"><parameterid>4</parameterid><name>Scale</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>5</parameterid><name>Horizontal Scale</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>6</parameterid><name> </name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>4</ParameterControlType><value>-91445760000000000,true,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>7</parameterid><name>Rotation</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>3</ParameterControlType><value>-91445760000000000,0.,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>8</parameterid><name>Opacity</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter><parameter authoringApp="PremierePro"><parameterid>9</parameterid><name>Anchor Point</name><IsTimeVarying>false</IsTimeVarying><value>-91445760000000000,0:0,0,0,0,0,0,0,5,4,0,0,0,0</value></parameter></effect></filter></clipitem>'
                    subtitle_clips += clip_xml
    
    track_subtitle = ""
    if subtitle_clips:
        track_subtitle = f"<track>{subtitle_clips}</track>"
    return track_subtitle
