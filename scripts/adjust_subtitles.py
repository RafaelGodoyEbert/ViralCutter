import json
import re
import os

def adjust(base_color, base_size, highlight_size, highlight_color, words_per_block, gap_limit, mode, vertical_position, alignment, font, outline_color, shadow_color, bold, italic, underline, strikeout, border_style, outline_thickness, shadow_size, project_folder="tmp"):
    def generate_ass(json_data, output_file, base_color=base_color, base_size=base_size, highlight_size=highlight_size, highlight_color=highlight_color, words_per_block=words_per_block, gap_limit=gap_limit, mode=mode, vertical_position=vertical_position, alignment=alignment, font=font, outline_color=outline_color, shadow_color=shadow_color, bold=bold, italic=italic, underline=underline, strikeout=strikeout, border_style=border_style, outline_thickness=outline_thickness, shadow_size=shadow_size):
        header_ass = f"""[Script Info]
    Title: Dynamic Subtitles
    ScriptType: v4.00+
    PlayDepth: 0

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

                        f.write(f"Dialogue: 0,{start_time_ass},{end_time_ass},Default,,0,0,0,,{line}\n")

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

            # Load JSON file
            with open(input_path, "r", encoding="utf-8") as file:
                json_data = json.load(file)
            
            # Determine alignment dynamically
            base_name = os.path.splitext(filename)[0] # e.g., final-output000_processed

            # Extract key matching edit_video log (outputXXX)
            # filenames are like "final-output000_processed.json" -> key "output000"
            key_match = re.search(r"(output\d+)", base_name)
            key = key_match.group(1) if key_match else base_name
            
            # Check for '2' mode
            current_alignment = alignment
            current_vertical_position = vertical_position
            
            mode_face = face_modes.get(key)

            if mode_face == "2":
                current_alignment = 5 # Center
                current_vertical_position = 0 # Middle
                print(f"  -> Video {base_name}: 2 Faces detected. Using Center Subtitles.")

            # Generate ASS file
            generate_ass(json_data, output_path, mode=mode, words_per_block=words_per_block, vertical_position=current_vertical_position, alignment=current_alignment)

            print(f"Processed file: {filename} -> {output_filename}")

    print("All JSON files processed and converted to ASS.")