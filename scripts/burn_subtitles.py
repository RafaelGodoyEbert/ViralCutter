import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def burn(project_folder="tmp"):
    # Converter para absoluto para não ter erro no filtro do ffmpeg
    if project_folder and not os.path.isabs(project_folder):
        project_folder_abs = os.path.abspath(project_folder)
    else:
        project_folder_abs = project_folder

    # Caminhos das pastas
    subs_folder = os.path.join(project_folder_abs, 'subs_ass')
    videos_folder = os.path.join(project_folder_abs, 'final')
    output_folder = os.path.join(project_folder_abs, 'burned_sub')  # Pasta para salvar os vídeos com legendas

    # Cria a pasta de saída se não existir
    os.makedirs(output_folder, exist_ok=True)
    
    if not os.path.exists(videos_folder):
        print(f"Pasta de vídeos finais não encontrada: {videos_folder}")
        return

    # Itera sobre os arquivos de vídeo na pasta final
    files = os.listdir(videos_folder)
    if not files:
        print("Nenhum arquivo encontrado em 'final' para queimar legendas.")
        return

    for video_file in files:
        if video_file.endswith(('.mp4', '.mkv', '.avi')):  # Formatos suportados
            # Se for temp file (ex: temp_video_no_audio), ignora se existir a versão final
            if "temp_video_no_audio" in video_file:
                continue

            # Extrai o nome base do vídeo (sem extensão)
            video_name = os.path.splitext(video_file)[0]
            
            # O edit_video gera 'final-outputXXX_processed'.
            # O transcribe_cuts gera SRT/JSON com base nisso.
            # O adjust gera ASS com base no JSON.
            # Então o nome deve bater.
            
            # Define o caminho para a legenda correspondente
            subtitle_file = os.path.join(subs_folder, f"{video_name}.ass")
            
            # Verifica se a legenda existe
            if os.path.exists(subtitle_file):
                # Define o caminho de saída para o vídeo com legendas
                output_file = os.path.join(output_folder, f"{video_name}_subtitled.mp4")

                # Ajuste no caminho da legenda para FFmpeg (Forward Slash e escape de :)
                # No Windows, "C:/foo" funciona se estiver entre aspas simples dentro do filtro.
                # Para garantir, usamos replace e forward slashes.
                subtitle_file_ffmpeg = subtitle_file.replace('\\', '/').replace(':', '\\:')

                # Funcao interna para encode logic
                def run_ffmpeg(encoder, preset, additional_args=[]):
                    cmd = [
                        "ffmpeg", "-y", "-loglevel", "error", "-hide_banner",
                        '-i', os.path.join(videos_folder, video_file),
                        '-vf', f"subtitles='{subtitle_file_ffmpeg}'",
                        '-c:v', encoder,
                        '-preset', preset,
                        '-b:v', '5M',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'copy',
                        output_file
                    ] + additional_args
                    subprocess.run(cmd, check=True, capture_output=True)

                # Tentar NVENC primeiro
                try:
                    print(f"Processando vídeo (NVENC): {video_file}")
                    run_ffmpeg("h264_nvenc", "p1")
                    print(f"Processado: {output_file}")
                except subprocess.CalledProcessError as e:
                    print(f"Erro com NVENC ({str(e)}). Tentando CPU (libx264)...")
                    try:
                        # Fallback CPU
                        run_ffmpeg("libx264", "ultrafast")
                        print(f"Processado (CPU): {output_file}")
                    except subprocess.CalledProcessError as e2:
                        print(f"ERRO FATAL ao queimar legendas em {video_name}: {e2}")
                        # Check output of ffmpeg if possible
                        if e2.stderr:
                             print(f"FFmpeg Log: {e2.stderr.decode('utf-8')}")
            else:
                print(f"Legenda não encontrada para: {video_name} em {subtitle_file}")

