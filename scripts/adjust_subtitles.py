import json
import re
import os

def adjust(base_color, base_size, highlight_size, highlight_color, words_per_block, gap_limit, mode, vertical_position, alignment, font, outline_color, shadow_color, bold, italic, underline, strikeout, border_style, outline_thickness, shadow_size, uppercase=False, project_folder="tmp", **kwargs):
    def generate_ass(json_data, output_file, base_color=base_color, base_size=base_size, highlight_size=highlight_size, highlight_color=highlight_color, words_per_block=words_per_block, gap_limit=gap_limit, mode=mode, vertical_position=vertical_position, alignment=alignment, font=font, outline_color=outline_color, shadow_color=shadow_color, bold=bold, italic=italic, underline=underline, strikeout=strikeout, border_style=border_style, outline_thickness=outline_thickness, shadow_size=shadow_size, uppercase=uppercase, timeline_data=None):
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
# Style: Default,{font},{base_size},{base_color},&H00000000,{outline_color},{shadow_color},{bold},{italic},{underline},{strikeout},100,100,0,0,1,1.5,0,{alignment},-2,-2,{vertical_position},1

#       1. **Name**: `Default` - Style name.
# 2. **Fontname**: `{font}` - Font name used.
# 3. **Fontsize**: `{base_size}` - Font size.
# 4. **PrimaryColour**: `{base_color}` - Primary text color.
#       5. **SecondaryColour**: `&H00000000` - Secondary text color (used for karaoke).
# 6. **OutlineColour**: `{outline_color}` - Text outline color.
# 7. **BackColour**: `{shadow_color}` - Text background/shadow color.
# 8. **Bold**: `{bold}` - Bold (1 to enable, 0 to disable).
# 9. **Italic**: `{italic}` - Italic (1 to enable, 0 to disable).
# 10. **Underline**: `{underline}` - Underline (1 to enable, 0 to disable).
# 11. **StrikeOut**: `{strikeout}` - Strikeout (1 to enable, 0 to disable).

#       12. **ScaleX**: `100` - Horizontal text scale (percentage).
#       13. **ScaleY**: `100` - Vertical text scale (percentage).
#       14. **Spacing**: `0` - Character spacing.
#        15. **Angle**: `0` - Text rotation angle.

# 16. **BorderStyle**: `{border_style}` - Border style (1 for outline, 3 for box).
# 17. **Outline**: `{outline_thickness}` - Outline thickness.
# 18. **Shadow**: `{shadow_size}` - Shadow size.
# 19. **Alignment**: `{alignment}` - Text alignment (1=bottom left, 2=bottom center, 3=bottom right, etc.)

#       20. **MarginL**: `-2` - Left margin.
#       21. **MarginR**: `-2` - Right margin.
#       22. **MarginV**: `60` - Vertical margin.
#       23. **Encoding**: `1` - Font encoding.

        with open(output_file, "w", encoding="utf-8") as f:
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

                        elif mode == "sem_higlight": 
                            line = " ".join(word_data['word'] for word_data in block).strip()

                        elif mode == "palavra_por_palavra": 
                            line = block[j]['word'].strip()

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
                                 # No pos tag needed, uses Style defaults (MarginV, Alignment)
                                 final_line = line
                        else:
                            final_line = line

                        f.write(f"Dialogue: 0,{start_time_ass},{end_time_ass},Default,,0,0,0,,{final_line}\n")

    def format_time_ass(time_seconds):
        hours = int(time_seconds // 3600)
        minutes = int((time_seconds % 3600) // 60)
        seconds = int(time_seconds % 60)
        centiseconds = int((time_seconds % 1) * 100)
        return f"{hours:01}:{minutes:02}:{seconds:02}.{centiseconds:02}"

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
            
            # Look for timeline file
            # filename is "final-outputXXX_processed.json"
            # timeline is "final-outputXXX_timeline.json" ? No, output_file was in 'final' folder
            # edit_video: timeline_file = output_file.replace(".mp4", "_timeline.json")
            # output_file was "final/temp_video_no_audio_{index}.mp4" -> "final/temp_video_no_audio_{index}_timeline.json"
            
            # We need to map filename to index to find timeline
            # Current filename: "final-output000_processed.json"
            match = re.search(r"output(\d+)", filename)
            timeline_data = None
            if match:
                 idx = int(match.group(1))
                 # Construct path to timeline
                 # edit_video saved it in 'final_folder' which is inside project_folder/final
                 # Pattern: temp_video_no_audio_{index}_timeline.json
                 timeline_path = os.path.join(project_folder, "final", f"temp_video_no_audio_{idx}_timeline.json")
                 if os.path.exists(timeline_path):
                     try:
                         with open(timeline_path, "r") as tf:
                             timeline_data = json.load(tf)
                         print(f"  -> Found dynamic timeline for video {idx}")
                     except:
                         pass

            # Load JSON file
            with open(input_path, "r", encoding="utf-8") as file:
                json_data = json.load(file)
            
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
                # print(f"  -> Video {base_name}: 2 Faces detected (static). Using Center Subtitles.")

            # Generate ASS file with dynamic timeline support
            generate_ass(json_data, output_path, mode=mode, words_per_block=words_per_block, 
                         vertical_position=current_vertical_position, alignment=current_alignment,
                         uppercase=uppercase,
                         timeline_data=timeline_data)

            print(f"Processed file: {filename} -> {output_filename}")

    print("All JSON files processed and converted to ASS.")