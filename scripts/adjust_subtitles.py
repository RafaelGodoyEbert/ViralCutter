import json
import re
import os

def format_time_ass(time_seconds):
    hours = int(time_seconds // 3600)
    minutes = int((time_seconds % 3600) // 60)
    seconds = int(time_seconds % 60)
    centiseconds = int((time_seconds % 1) * 100)
    return f"{hours:01}:{minutes:02}:{seconds:02}.{centiseconds:02}"

def generate_ass_from_file(input_path, output_path, project_folder, 
                           base_color, base_size, highlight_size, highlight_color, 
                           words_per_block, gap_limit, mode, vertical_position, alignment, 
                           font, outline_color, shadow_color, bold, italic, underline, 
                           strikeout, border_style, outline_thickness, shadow_size, uppercase,
                           face_modes={}):
    """
    Generates a single ASS file from a JSON input.
    """
    
    # 1. Load Timeline Data (if exists)
    filename = os.path.basename(input_path)
    match = re.search(r"output(\d+)", filename)
    timeline_data = None
    if match:
         idx = int(match.group(1))
         # Construct path to timeline
         csv_timeline = os.path.join(project_folder, "final", f"temp_video_no_audio_{idx}_timeline.json")
         if os.path.exists(csv_timeline):
             try:
                 with open(csv_timeline, "r") as tf:
                     timeline_data = json.load(tf)
             except:
                 pass
    
    # 2. Determine Style Overrides (Face Mode)
    # Determine static alignment (fallback)
    base_name = os.path.splitext(filename)[0] 
    key_match = re.search(r"(output\d+)", base_name)
    key = key_match.group(1) if key_match else base_name
    
    current_alignment = alignment
    current_vertical_position = vertical_position
    
    mode_face = face_modes.get(key)
    if mode_face == "2" and not timeline_data: # Only use static if no timeline
        current_alignment = 5 
        current_vertical_position = 0 

    # 3. Load JSON
    try:
        with open(input_path, "r", encoding="utf-8") as file:
            json_data = json.load(file)
        
        segments_count = len(json_data.get('segments', []))
        print(f"[DEBUG] Loaded {input_path}: Found {segments_count} segments.")
    except Exception as e:
        print(f"[ERROR] Loading JSON {input_path}: {e}")
        return

    # 4. Generate Content
    header_ass = f"""[Script Info]
    Title: Dynamic Subtitles
    ScriptType: v4.00+
    PlayDepth: 0
    PlayResX: 360
    PlayResY: 640

    [V4+ Styles]
    Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    Style: Default,{font},{base_size},{base_color},&H00000000,{outline_color},{shadow_color},{bold},{italic},{underline},{strikeout},100,100,0,0,{border_style},{outline_thickness},{shadow_size},{alignment},-2,-2,{vertical_position},1

    [Events]
    Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    """
    
    total_lines_written = 0
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header_ass)


        last_end_time = 0.0

        for segment in json_data.get('segments', []):
            words = segment.get('words', [])
            total_words = len(words)

            i = 0
            while i < total_words:
                block = []
                while len(block) < words_per_block and i < total_words:
                    current_word = words[i]
                    if 'word' in current_word:
                        cleaned_word = re.sub(r'[.,!?;]', '', current_word['word'])
                        block.append({**current_word, 'word': cleaned_word})

                        if i + 1 < total_words:
                            next_word = words[i + 1]
                            if 'start' not in next_word or 'end' not in next_word:
                                next_cleaned_word = re.sub(r'[.,!?;]', '', next_word['word'])
                                block[-1]['word'] += " " + next_cleaned_word
                                i += 1
                    i += 1


                # Uppercase transformation
                if uppercase:
                     for w_item in block:
                         if 'word' in w_item:
                             w_item['word'] = w_item['word'].upper()

                start_times = [word.get('start', 0) for word in block]
                end_times = [word.get('end', 0) for word in block]
                
                if not start_times: continue

                for j in range(len(block)):
                    start_sec = start_times[j]
                    end_sec = end_times[j]

                    # Prevent overlap and close gaps
                    if start_sec - last_end_time < gap_limit:
                        start_sec = last_end_time

                    # Ensure valid duration
                    if end_sec < start_sec:
                        end_sec = start_sec

                    start_time_ass = format_time_ass(start_sec)
                    end_time_ass = format_time_ass(end_sec)
                    
                    last_end_time = end_sec

                    line = ""
                    if mode == "highlight":
                        for k, word_data in enumerate(block):
                            word = word_data['word']
                            if k == j:
                                line += f"{{\\fs{highlight_size}\\c{highlight_color}}}{word} "
                            else:
                                line += f"{{\\fs{base_size}\\c{base_color}}}{word} "
                        line = line.strip()

                        line = line.strip()

                    elif mode == "no_highlight" or mode == "sem_higlight": 
                        line = " ".join(word_data['word'] for word_data in block).strip()

                    elif mode == "palavra_por_palavra": 
                        line = block[j]['word'].strip()
                    
                    else:
                        # Fallback / No Highlight
                        line = " ".join(word_data['word'] for word_data in block).strip()

                    # Check dynamic timeline for this specific time
                    pos_tag = ""
                    
                    if timeline_data:
                        # Verify if middle of subtitle is in a '2' mode segment
                        mid_time = (start_sec + end_sec) / 2
                        found_mode = "1"
                        for seg in timeline_data:
                            if seg['start'] <= mid_time <= seg['end']:
                                found_mode = seg['mode']
                                break
                        
                        if found_mode == "2":
                             # Force Center (Relative to PlayRes 360x640)
                             x_pos = 360 // 2  # 180
                             y_pos = 640 // 2  # 320
                             current_line_alignment = 5 # Center
                             
                             # Apply Override Tags: {\an5\pos(x,y)}
                             pos_tag = f"{{\\an{current_line_alignment}\\pos({x_pos},{y_pos})}}"
                             final_line = f"{pos_tag}{line}"
                        else:
                             # Mode 1: Respect User Config (Standard Style)
                             final_line = line
                    else:
                        final_line = line

                    f.write(f"Dialogue: 0,{start_time_ass},{end_time_ass},Default,,0,0,0,,{final_line}\n")
                    total_lines_written += 1
    
    if total_lines_written == 0:
        print(f"[WARN] No dialogue lines written for {input_path}")
    else:
        print(f"[DEBUG] Wrote {total_lines_written} lines to {output_path}")


def adjust(base_color, base_size, highlight_size, highlight_color, words_per_block, gap_limit, mode, vertical_position, alignment, font, outline_color, shadow_color, bold, italic, underline, strikeout, border_style, outline_thickness, shadow_size, uppercase=False, project_folder="tmp", **kwargs):
    
    # Input and Output Directories
    input_dir = os.path.join(project_folder, "subs")
    output_dir = os.path.join(project_folder, "subs_ass")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load face modes if available
    face_modes = {}
    modes_file = os.path.join(project_folder, "face_modes.json")
    if os.path.exists(modes_file):
        try:
             with open(modes_file, "r") as f:
                 face_modes = json.load(f)
             print("Loaded face modes for dynamic subtitle positioning.")
        except Exception as e:
            print(f"Could not load face modes: {e}")

    # Process all JSON files in input directory
    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            input_path = os.path.join(input_dir, filename)
            output_filename = os.path.splitext(filename)[0] + ".ass"
            output_path = os.path.join(output_dir, output_filename)
            
            generate_ass_from_file(input_path, output_path, project_folder, 
                           base_color, base_size, highlight_size, highlight_color, 
                           words_per_block, gap_limit, mode, vertical_position, alignment, 
                           font, outline_color, shadow_color, bold, italic, underline, 
                           strikeout, border_style, outline_thickness, shadow_size, uppercase,
                           face_modes)

            print(f"Processed file: {filename} -> {output_filename}")

    print("All JSON files processed and converted to ASS.")