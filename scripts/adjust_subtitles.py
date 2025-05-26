import json
import re
import os

def adjust(base_color, base_size, h_size, highlight_color, words_per_block, gap_limit, mode, vertical_position, alignment, font, outline, shadow_color, bold, italic, underline, strikeout, border_style, outline_thickness, shadow_size):
    def generate_ass(json_data, output_file, base_color=base_color, base_size=base_size, h_size=h_size, highlight_color=highlight_color, words_per_block=words_per_block, gap_limit=gap_limit, mode=mode, vertical_position=vertical_position, alignment=alignment, font=font, outline=outline, shadow_color=shadow_color, bold=bold, italic=italic, underline=underline, strikeout=strikeout, border_style=border_style, outline_thickness=outline_thickness, shadow_size=shadow_size):
        header_ass = f"""[Script Info]
    Title: Dynamic Subtitles
    ScriptType: v4.00+
    PlayDepth: 0

    [V4+ Styles]
    Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    Style: Default,{font},{base_size},{base_color},&H00000000,{outline},{shadow_color},{bold},{italic},{underline},{strikeout},100,100,0,0,{border_style},{outline_thickness},{shadow_size},{alignment},-2,-2,{vertical_position},1

    [Events]
    Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    """
# Style: Default,{font},{base_size},{base_color},&H00000000,{outline},{shadow_color},{bold},{italic},{underline},{strikeout},100,100,0,0,1,1.5,0,{alignment},-2,-2,{vertical_position},1

#       1. **Name**: `Default` - Style name.
# 2. **Fontname**: `{font}` - Font name used.
# 3. **Fontsize**: `{base_size}` - Font size.
# 4. **PrimaryColour**: `{base_color}` - Primary text color.
#       5. **SecondaryColour**: `&H00000000` - Secondary text color (used for karaoke).
# 6. **OutlineColour**: `{outline}` - Text outline color.
# 7. **BackColour**: `{shadow_color}` - Text background color.
# 8. **Bold**: `{bold}` - Bold (1 to activate, 0 to deactivate).
# 9. **Italic**: `{italic}` - Italic (1 to activate, 0 to deactivate).
# 10. **Underline**: `{underline}` - Underline (1 to activate, 0 to deactivate).
# 11. **StrikeOut**: `{strikeout}` - Strikeout (1 to activate, 0 to deactivate).

#       12. **ScaleX**: `100` - Horizontal text scale (in percentage).
#       13. **ScaleY**: `100` - Vertical text scale (in percentage).
#       14. **Spacing**: `0` - Character spacing.
#        15. **Angle**: `0` - Text rotation angle.

# 16. **BorderStyle**: `{border_style}` - Border style (1 for outline, 3 for box).
# 17. **Outline**: `{outline_thickness}` - Outline thickness.
# 18. **Shadow**: `{shadow_size}` - Shadow size.
# 19. **Alignment**: `{alignment}` - Text alignment (1 = bottom left, 2 = bottom center, 3 = bottom right, 4 = middle left, 5 = middle center, 6 = middle right, 7 = top left, 8 = top center, 9 = top right)

#       20. **MarginL**: `-2` - Left margin.
#       21. **MarginR**: `-2` - Right margin.
#       22. **MarginV**: `60` - Vertical margin.
#       23. **Encoding**: `1` - Font encoding (0 for ANSI, 1 for Default, etc.).

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(header_ass)

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

                    if mode == "highlight":
                        for j in range(len(block)):
                            line = ""
                            for k, word_data in enumerate(block):
                                word = word_data['word']
                                if k == j:
                                    line += f"{{\\fs{h_size}\\c{highlight_color}}}{word} "
                                else:
                                    line += f"{{\\fs{base_size}\\c{base_color}}}{word} "

                            start_time_ass = format_time_ass(start_times[j])
                            if j > 0 and (start_times[j] - end_times[j - 1] < gap_limit):
                                start_time_ass = format_time_ass(end_times[j - 1])

                            end_time_ass = format_time_ass(end_times[j])

                            f.write(f"Dialogue: 0,{start_time_ass},{end_time_ass},Default,,0,0,0,,{line.strip()}\n")

                    elif mode == "no_highlight":
                        for j in range(len(block)):
                            line = " ".join(word_data['word'] for word_data in block)

                            start_time_ass = format_time_ass(start_times[j])
                            if j > 0 and (start_times[j] - end_times[j - 1] < gap_limit):
                                start_time_ass = format_time_ass(end_times[j - 1])

                            end_time_ass = format_time_ass(end_times[j])

                            f.write(f"Dialogue: 0,{start_time_ass},{end_time_ass},Default,,0,0,0,,{line.strip()}\n")

                    elif mode == "word_by_word":
                        for j in range(len(block)):
                            line = block[j]['word']
                            start_time_ass = format_time_ass(start_times[j])
                            end_time_ass = format_time_ass(end_times[j])
                            f.write(f"Dialogue: 0,{start_time_ass},{end_time_ass},Default,,0,0,0,,{line.strip()}\n")

    def format_time_ass(time_seconds):
        hours = int(time_seconds // 3600)
        minutes = int((time_seconds % 3600) // 60)
        seconds = int(time_seconds % 60)
        centiseconds = int((time_seconds % 1) * 100)
        return f"{hours:01}:{minutes:02}:{seconds:02}.{centiseconds:02}"

    # Input and output directories
    input_dir = "subs"
    output_dir = "subs_ass"

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Process all JSON files in the input folder
    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            input_path = os.path.join(input_dir, filename)
            output_filename = os.path.splitext(filename)[0] + ".ass"
            output_path = os.path.join(output_dir, output_filename)

            # Load JSON file
            with open(input_path, "r", encoding="utf-8") as file:
                json_data = json.load(file)

            # Generate ASS file
            generate_ass(json_data, output_path, mode=mode, words_per_block=words_per_block, vertical_position=vertical_position, alignment=alignment)

            print(f"File processed: {filename} -> {output_filename}")

    print("All JSON files have been processed and converted to ASS.")