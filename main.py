import os
from scripts import download_video, transcribe_video, create_viral_segments, cut_segments, edit_video, transcribe_cuts, adjust_subtitles, burn_subtitles, save_json

# Create necessary directories
os.makedirs('tmp', exist_ok=True)
os.makedirs('final', exist_ok=True)
os.makedirs('subs', exist_ok=True)
os.makedirs('subs_ass', exist_ok=True)
os.makedirs('burned_sub', exist_ok=True)

# Input variables
url = input("Enter the YouTube video URL: ")
num_segments = int(input("Enter the number of viral segments to create: "))
viral_mode = True
themes = input("Enter themes (comma-separated, leave blank if viral mode is True): ") if not viral_mode else ''

# Transcript variables
model = 'large-v3'

# Subtitle variables
base_color = "White"
base_size = 12
highlight_size = 14
highlight_color = "&H00FF00&"
words_per_block = 5
gap_limit = 0.5
subtitle_mode = 'highlight'
vertical_position = 60
alignment = 2

# Burn subtitles option
burn_subtitles_option = True

# Execute the pipeline
input_video = download_video.download(url)
srt_file, tsv_file = transcribe_video.transcribe(input_video, model)

# First, create viral segments
viral_segments = create_viral_segments.create(num_segments, viral_mode, themes)

# Check if the viral_segments file exists, and handle input accordingly
save_json.save_viral_segments(viral_segments)

# You can uncomment these steps when ready to process them
cut_segments.cut(viral_segments)
edit_video.edit()

# Burn subtitles if the option is set to true
if burn_subtitles_option:
    transcribe_cuts.transcribe()
    adjust_subtitles.adjust(base_color, base_size, highlight_size, highlight_color, words_per_block, gap_limit, subtitle_mode, vertical_position, alignment)
    burn_subtitles.burn()
else:
    print("Subtitle burning skipped.")

print("Process completed successfully!")
