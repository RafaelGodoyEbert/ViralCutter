import os
import yt_dlp

def download(url):
    output_path = 'tmp/input_video.mp4'
    
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
                print("Erro: o link inserido não é válido.")
                url = input("\nPor favor, insira um link válido: ")
            else:
                raise

    return output_path