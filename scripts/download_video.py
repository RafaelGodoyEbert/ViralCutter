import os
import yt_dlp
import subprocess

def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ], capture_output=True, text=True)
        return float(result.stdout.strip())
    except:
        return None

def get_video_info(url):
    """Get video info including duration from URL without downloading"""
    try:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('duration'), info.get('id'), info.get('title')
    except:
        return None, None, None

def download(url):
    output_path = 'tmp/input_video.mp4'
    
    # Check if video already exists and compare with new URL
    should_download = True
    if os.path.exists(output_path):
        current_duration = get_video_duration(output_path)
        new_duration, new_id, new_title = get_video_info(url)
        
        if current_duration and new_duration:
            duration_diff = abs(current_duration - new_duration)
            if duration_diff < 5:  # Allow 5 second tolerance
                print(f"Video with similar duration already exists ({int(current_duration)}s vs {int(new_duration)}s)")
                response = input("Download new video anyway? (y/n): ").lower()
                should_download = response in ['y', 'yes']
            else:
                print(f"Different video detected - existing: {int(current_duration)}s, new: {int(new_duration)}s")
                print("Downloading new video...")
                os.remove(output_path)
    
    if should_download:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat':'mp4'
            }],
            'outtmpl': output_path,
            'postprocessor_args': [
                '-movflags', 'faststart'
            ],
           'merge_output_format':'mp4'
        }

        while True:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                break
            except yt_dlp.utils.DownloadError as e:
                if "is not a valid URL" in str(e):
                    print("Error: The entered link is not valid.")
                    url = input("\nPlease enter a valid link: ")
                else:
                    raise

    duration = get_video_duration(output_path)
    return output_path, duration