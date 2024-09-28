import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def burn():
    # Caminhos das pastas
    subs_folder = 'subs_ass'
    videos_folder = 'final'
    output_folder = 'burned_sub'  # Pasta para salvar os vídeos com legendas

    # Cria a pasta de saída se não existir
    os.makedirs(output_folder, exist_ok=True)

    # Itera sobre os arquivos de vídeo na pasta final
    for video_file in os.listdir(videos_folder):
        if video_file.endswith(('.mp4', '.mkv', '.avi')):  # Formatos suportados
            # Extrai o nome base do vídeo (sem extensão)
            video_name = os.path.splitext(video_file)[0]

            # Define o caminho para a legenda correspondente
            subtitle_file = os.path.join(subs_folder, f"{video_name}.ass")
            print(f"Caminho da legenda: {subtitle_file}")

            # Verifica se a legenda existe
            if os.path.exists(subtitle_file):
                # Define o caminho de saída para o vídeo com legendas
                output_file = os.path.join(output_folder, f"{video_name}_subtitled.mp4")

                # Ajuste no caminho da legenda para FFmpeg
                subtitle_file_ffmpeg = subtitle_file.replace('\\', '/')

                # Comando FFmpeg para adicionar as legendas
                command = [
                    'ffmpeg',
                    '-i', os.path.join(videos_folder, video_file),  # Vídeo de entrada
                    '-vf', f"subtitles='{subtitle_file_ffmpeg}'",  # Filtro de legendas com caminho corrigido
                    '-c:v', 'h264_nvenc',  # Codificador NVIDIA
                    '-preset', 'p1',  # Preset para velocidade
                    '-b:v', '5M',  # Bitrate
                    '-c:a', 'copy',  # Copia o áudio
                    output_file
                ]

                # Log dos caminhos e do comando
                print(f"Processando vídeo: {video_file}")
                print(f"Caminho da legenda: {subtitle_file}")
                print(f"Caminho de saída: {output_file}")
                print(f"Comando: {' '.join(command)}")

                # Executa o comando
                try:
                    subprocess.run(command, check=True)
                    print(f"Processado: {output_file}")
                except subprocess.CalledProcessError as e:
                    print(f"Erro ao processar {video_name}: {e}")
            else:
                print(f"Legenda não encontrada para: {video_name}")

