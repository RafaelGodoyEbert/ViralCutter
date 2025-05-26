import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def burn():
    # Folder paths
    subs_folder = 'subs_ass'
    videos_folder = 'final'
    output_folder = 'burned_sub'  # Folder to save videos with subtitles

    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Iterate over video files in the final folder
    for video_file in os.listdir(videos_folder):
        if video_file.endswith(('.mp4', '.mkv', '.avi')):  # Supported formats
            # Extract base video name (without extension)
            video_name = os.path.splitext(video_file)[0]

            # Define path for corresponding subtitle
            subtitle_file = os.path.join(subs_folder, f"{video_name}.ass")
            print(f"Subtitle path: {subtitle_file}")

            # Check if subtitle exists
            if os.path.exists(subtitle_file):
                # Define output path for video with subtitles
                output_file = os.path.join(output_folder, f"{video_name}_subtitled.mp4")

                # Adjust subtitle path for FFmpeg
                subtitle_file_ffmpeg = subtitle_file.replace('\\', '/')

                # FFmpeg command to add subtitles
                command = [
                    'ffmpeg',
                    '-i', os.path.join(videos_folder, video_file),  # Input video
                    '-vf', f"subtitles='{subtitle_file_ffmpeg}'",  # Subtitle filter with corrected path
                    '-c:v', 'h264_nvenc',  # NVIDIA encoder
                    '-preset', 'p1',  # Speed preset
                    '-b:v', '5M',  # Video bitrate
                    '-c:a', 'copy',  # Copy audio
                    output_file
                ]

                # Log paths and command
                print(f"Processing video: {video_file}")
                print(f"Subtitle path: {subtitle_file}")
                print(f"Output path: {output_file}")
                print(f"Command: {' '.join(command)}")

                # Execute command
                try:
                    subprocess.run(command, check=True)
                    print(f"Processed: {output_file}")
                except subprocess.CalledProcessError as e:
                    print(f"Error processing {video_name}: {e}")
            else:
                print(f"Subtitle not found for: {video_name}")

