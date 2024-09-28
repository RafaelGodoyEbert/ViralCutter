import os
import yt_dlp

def download(url):
    output_path = 'tmp/input_video.mp4'
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        }],
        'outtmpl': output_path,
        'postprocessor_args': [
            '-movflags', 'faststart'
        ],
        'merge_output_format': 'mp4'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    return output_path