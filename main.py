import os
from scripts import download_video, transcribe_video, create_viral_segments, cut_segments, edit_video, transcribe_cuts, adjust_subtitles, burn_subtitles, save_json
from i18n.i18n import I18nAuto
i18n = I18nAuto()

# Create necessary directories
os.makedirs('tmp', exist_ok=True)
os.makedirs('final', exist_ok=True)
os.makedirs('subs', exist_ok=True)
os.makedirs('subs_ass', exist_ok=True)
os.makedirs('burned_sub', exist_ok=True)

# Original inverted colors
red = "0A08E4"
yellow = "00FFFF" 
blue = "700206"
black = "000000" 
green = "58DA7D" 
white = "FFFFFF"
orange = "0099FE" 
purple = "800080"
pink = "C77DF9"
cyan = "FFFF00" 
brown = "2D4A8C"
gray = "808080" 
lime_green = "32CD32" 
light_blue = "E6D8AD" 
green = "0FF00"

# Subtitle variables
font = "Arial" # Arial, Times New Roman # In colab all Google Fonts, in Windows/Linux the ones installed on your system
base_size = 12 # 12
base_color_t = "00" # 00= completely opaque, 80= 50% transparent, FF= Completely transparent
base_color = f"&H{base_color_t}" + "FFFFFF" + "&" # FFFFFF (white) or 00FFFF (yellow)
outline_t = "FF" # 00= completely opaque, 80= 50% transparent, FF= Completely transparent
outline = f"&H{outline_t}" + "808080" + "&" # 808080
h_size = 14 # 14 (Default)
words_per_block = 3 # 5 (Default)
gap_limit = 0.5 # 0.5 (Default)
mode = 'highlight' # no_highlight, word_by_word, highlight
highlight_color_t = "00" # 00= completely opaque, 80= 50% transparent, FF= Completely transparent
highlight_color = f"&H{highlight_color_t}" + "0FF00" + "&" # 0FF00
vertical_position = 60 # Divide from 1 to 5 counting one at the top. 1=170, 2=130, 3=99, 4=60 (default), 5=20
shadow_color_t = "00" # 00= completely opaque, 80= 50% transparent, FF= Completely transparent
shadow_color = f"&H{shadow_color_t}" + "000000" + "&" # 000000
alignment = 2 # 1= Left, 2= Center (default), 3= Right
bold = 0 # (1 to activate, 0 to deactivate)
italic = 0 # (1 to activate, 0 to deactivate)
underline = 0 # (1 to activate, 0 to deactivate)
strikeout = 0 # (1 to activate, 0 to deactivate)
border_style = 3 # (1 for outline, 3 for box)
outline_thickness = 1.5 # 1.5 (Default)
shadow_size = 10 # 10 (Default)

# Burn subtitles option
burn_only = False
burn_subtitles_option = True

# Transcript variables
model = 'large-v3'

if burn_only:
    print(i18n("Burn only mode activated. Skipping to subtitle burning..."))
    burn_subtitles.burn()
    print(i18n("Subtitle burning completed."))
else:
    # Input variables
    url = input(i18n("Enter the YouTube video URL: "))

    # Execute the pipeline
    input_video, video_duration = download_video.download(url)
    
    # Calculate recommended max segments based on video duration
    if video_duration:
        min_duration = 15  # minimum segment duration in seconds
        max_duration = 90  # maximum segment duration in seconds
        recommended_max = int(video_duration // min_duration)
        video_minutes = int(video_duration // 60)
        video_seconds = int(video_duration % 60)
        print(i18n(f"\nVideo duration: {video_minutes}m {video_seconds}s"))
        print(i18n(f"Recommended maximum segments: {recommended_max} (based on {min_duration}s minimum per segment)"))
    
    while True:
        try:
            num_segments = int(input(i18n("Enter the number of viral segments to create: ")))
            if num_segments < 1:
                print(i18n("\nError: Number of segments must be numeric and greater than 0."))
            else:
                break
        except ValueError:
            print(i18n("\nError: The value you entered is not an integer. Please try again."))
        
    viral_mode = input(i18n("Do you want viral mode? (yes/no): ")).lower() == 'yes' or 'y'
    themes = input(i18n("Enter themes (comma-separated, leave blank if viral mode is True): ")) if not viral_mode else ''
    
    min_duration = 15 #int(input("Enter the minimum duration for segments (in seconds): "))
    max_duration = 90 #int(input("Enter the maximum duration for segments (in seconds): "))

    srt_file, tsv_file = transcribe_video.transcribe(input_video, model)

    viral_segments = create_viral_segments.create(num_segments, viral_mode, themes, min_duration, max_duration)
    save_json.save_viral_segments(viral_segments)

    cut_segments.cut(viral_segments)
    edit_video.edit()

    if burn_subtitles_option:
        transcribe_cuts.transcribe()
        adjust_subtitles.adjust(base_color, base_size, h_size, highlight_color, words_per_block, gap_limit, mode, vertical_position, alignment, font, outline, shadow_color, bold, italic, underline, strikeout, border_style, outline_thickness, shadow_size)
        burn_subtitles.burn()
    else:
        print(i18n("Subtitle burning skipped."))

    print(i18n("Process completed successfully!"))