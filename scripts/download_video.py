import os
import re
import yt_dlp

def sanitize_filename(name):
    """Remove caracteres inválidos para nomes de arquivos/pastas."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    cleaned = cleaned.strip()
    return cleaned

def download(url, base_root="VIRALS"):
    # 1. Extrair informações do vídeo (sem baixar) para pegar o título
    print("Extraindo informações do vídeo...")
    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'cookiesfrombrowser': ('chrome',)}) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Untitled_Video')
            safe_title = sanitize_filename(title)
        except Exception as e:
            print(f"Erro ao obter informações do vídeo: {e}")
            safe_title = "Unknown_Video"

    # 2. Criar estrutura de pastas
    project_folder = os.path.join(base_root, safe_title)
    os.makedirs(project_folder, exist_ok=True)
    
    # Caminho final do vídeo
    # O yt-dlp com 'outtmpl' e merge_output_format mp4 vai gerar .mp4
    # Mas precisamos garantir que seja exatamente 'input.mp4' para facilitar
    output_filename = 'input' # sem extensao pro ydl botar
    output_path_base = os.path.join(project_folder, output_filename)
    final_video_path = f"{output_path_base}.mp4"

    # Verificação inteligente: Se o arquivo já existe, reutiliza sem baixar de novo.
    if os.path.exists(final_video_path):
        # Validação simples de tamanho (evita arquivos vazios de falhas anteriores)
        if os.path.getsize(final_video_path) > 1024: # > 1KB
            print(f"Vídeo já existe em: {final_video_path}")
            print("Pulando download e reutilizando arquivo local.")
            return final_video_path, project_folder
        else:
            print("Arquivo existente encontrado mas parece corrompido/vazio. Baixando novamente...")
            try:
                os.remove(final_video_path)
            except:
                pass

    # Limpeza de temp
    temp_path = f"{output_path_base}.temp.mp4"
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except:
            pass

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'overwrites': True,
        # 'outtmpl' define o nome base.
        # 'merge_output_format' garante que se houver merge (video+audio), será mp4.
        # Removemos o FFmpegVideoConvertor explícito para evitar conflito de rename no Windows.
        'outtmpl': output_path_base, 
        'postprocessor_args': [
            '-movflags', 'faststart'
        ],
       'merge_output_format':'mp4'
       
    }

    print(f"Baixando vídeo para: {project_folder}...")
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

    return final_video_path, project_folder