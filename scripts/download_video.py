import os
import re
import yt_dlp
import sys

def sanitize_filename(name):
    """Remove caracteres inválidos para nomes de arquivos/pastas."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    cleaned = cleaned.strip()
    return cleaned

def progress_hook(d):
    if d['status'] == 'downloading':
        try:
            p = d.get('_percent_str', '').replace('%','')
            print(f"[download] {p}% - {d.get('_eta_str', 'N/A')} remaining", flush=True)
        except:
            pass
    elif d['status'] == 'finished':
        print(f"[download] Download concluído: {d['filename']}", flush=True)

def download(url, base_root="VIRALS", download_subs=True, quality="best"):
    # 1. Extrair informações do vídeo para pegar o título
    print("Extraindo informações do vídeo...")
    title = None
    
    # ... (Keep existing title extraction logic) ...
    # Instead of repeating it effectively, I will rely on the diff to keep it or re-write it if I have to replace the whole block.
    # Since replace_file_content works on line ranges, I should be careful.
    # Let's assume I'm replacing the whole function body or significant parts.
    
    # Tentativa 1: Com cookies
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'cookiesfrombrowser': ('chrome',)}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title')
    except Exception as e:
        print(f"Aviso: Falha ao extrair info com cookies: {e}")
        
    # Tentativa 2: Sem cookies
    if not title:
        try:
             with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title')
        except Exception as e:
            print(f"Erro ao obter informações do vídeo (sem cookies): {e}")

    # Fallback final
    if title:
        safe_title = sanitize_filename(title)
        print(f"Título detectado: {title}")
    else:
        print("AVISO: Título não pôde ser obtido. Usando 'Unknown_Video'.")
        safe_title = "Unknown_Video"

    # 2. Criar estrutura de pastas
    project_folder = os.path.join(base_root, safe_title)
    os.makedirs(project_folder, exist_ok=True)
    
    # Caminho final do vídeo
    output_filename = 'input' 
    output_path_base = os.path.join(project_folder, output_filename)
    final_video_path = f"{output_path_base}.mp4"

    # Verificação inteligente
    if os.path.exists(final_video_path):
        if os.path.getsize(final_video_path) > 1024: 
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

    # Mapeamento de Qualidade
    quality_map = {
        "best": 'bestvideo+bestaudio/best',
        "1080p": 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        "720p": 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        "480p": 'bestvideo[height<=480]+bestaudio/best[height<=480]'
    }
    selected_format = quality_map.get(quality, 'bestvideo+bestaudio/best')
    print(f"Configurando qualidade de download: {quality} -> {selected_format}")

    ydl_opts = {
        'format': selected_format,
        'overwrites': True,
        'outtmpl': output_path_base, 
        'postprocessor_args': [
            '-movflags', 'faststart'
        ],
        'merge_output_format': 'mp4',
        'progress_hooks': [progress_hook],
        # Opções de Legenda
        'writesubtitles': download_subs,
        'writeautomaticsub': download_subs,
        'subtitleslangs': ['pt.*', 'en.*', 'sp.*'], # Prioritize generic PT, EN, SP
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        'skip_download': False,
        'quiet': False,
        'no_warnings': False,
    }
    

    
    if download_subs:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegSubtitlesConvertor',
            'format': 'srt',
        }]

    print(f"Baixando vídeo para: {project_folder}...")
    
    # Tentativa 1: Com configuração original
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        error_str = str(e)
        if download_subs and ("Unable to download video subtitles" in error_str or "429" in error_str):
            print(f"\nAviso: Erro ao baixar legendas ({e}).")
            print("Tentando novamente APENAS o vídeo (sem legendas)...")
            
            ydl_opts['writesubtitles'] = False
            ydl_opts['writeautomaticsub'] = False
            ydl_opts['postprocessors'] = [p for p in ydl_opts.get('postprocessors', []) if 'Subtitle' not in p.get('key', '')]
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e2:
                print(f"Erro fatal na segunda tentativa: {e2}")
                raise
        elif "is not a valid URL" in error_str:
             print("Erro: o link inserido não é válido.")
             raise 
        else:
            print(f"Erro no download: {e}")
            raise
    except Exception as e:
        print(f"Erro inesperado: {e}")
        raise

    # RENOMEAR LEGENDA PARA PADRÃO (input.vtt ou input.srt)
    # Se for VTT, converte para SRT para garantir compatibilidade.
    try:
        import glob
        # Pega a primeira que encontrar
        potential_subs = glob.glob(os.path.join(project_folder, "input.*.vtt")) + glob.glob(os.path.join(project_folder, "input.*.srt"))
        
        if potential_subs:
            best_sub = potential_subs[0]
            ext = os.path.splitext(best_sub)[1]
            new_name = os.path.join(project_folder, "input.srt") # Vamos padronizar tudo para .srt
            
            if ext.lower() == '.vtt':
                print(f"Formatando legenda VTT complexa ({os.path.basename(best_sub)}) para SRT limpo...")
                try:
                    with open(best_sub, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    srt_content = []
                    counter = 1
                    
                    seen_texts = set()
                    last_text = ""
                    
                    for line in lines:
                        clean_line = line.strip()
                        # Ignora Headers e Metadados do VTT/Youtube
                        if clean_line.startswith("WEBVTT") or \
                           clean_line.startswith("X-TIMESTAMP") or \
                           clean_line.startswith("NOTE") or \
                           clean_line.startswith("Kind:") or \
                           clean_line.startswith("Language:"):
                            continue
                        
                        if "-->" in clean_line:
                            # Parse Timestamp
                            parts = clean_line.split("-->")
                            start = parts[0].strip()
                            # Remove tags de posicionamento "align:start position:0%"
                            end = parts[1].strip().split(' ')[0] 
                            
                            def fix_time(t):
                                t = t.replace('.', ',')
                                if t.count(':') == 1: 
                                    t = "00:" + t
                                return t
                            
                            current_start = fix_time(start)
                            current_end = fix_time(end)
                            
                        elif clean_line:
                             # Texto: remover tags complexas <00:00:00.560><c> etc
                             # O YouTube usa formato karaoke. Ex: "Quanto<...> custa<...>"
                             # Precisamos do texto limpo.
                             text = re.sub(r'<[^>]+>', '', clean_line).strip()
                             
                             if not text: continue
                             
                             # Lógica para remover duplicatas do estilo "Roll-up" ou "Karaoke"
                             # O YouTube repete a linha anterior às vezes.
                             # Ex:
                             # 1: "Quanto custa"
                             # 2: "Quanto custa\nQuantos quilos"
                             
                             # Vamos pegar apenas a ULTIMA linha se tiver quebras
                             lines_in_text = text.split('\n')
                             final_line = lines_in_text[-1].strip()
                             
                             if not final_line: continue

                             # Filtro de duplicidade consecutivo
                             if final_line == last_text:
                                 continue
                             
                             # Evita blocos ultra curtos (glitch de 10ms) que repetem texto
                             # Mas aqui estamos processando texto.
                             
                             srt_content.append(f"{counter}\n")
                             srt_content.append(f"{current_start} --> {current_end}\n")
                             srt_content.append(f"{final_line}\n\n")
                             
                             last_text = final_line
                             counter += 1
                    
                    with open(new_name, 'w', encoding='utf-8') as f_out:
                        f_out.writelines(srt_content)
                    
                    print(f"Legenda convertida e limpa: {new_name}")
                    try: os.remove(best_sub) 
                    except: pass
                    
                except Exception as e_conv:
                    print(f"Falha ao converter VTT: {e_conv}. Mantendo original.")
                    # Fallback: rename apenas
                    new_name_fallback = os.path.join(project_folder, "input.vtt")
                    if os.path.exists(new_name_fallback) and new_name_fallback != best_sub:
                        try: os.remove(new_name_fallback)
                        except: pass
                    os.rename(best_sub, new_name_fallback)

            else:
                # Já é SRT, só renomeia
                if os.path.exists(new_name) and new_name != best_sub:
                    try: os.remove(new_name)
                    except: pass
                os.rename(best_sub, new_name)
                print(f"Legenda SRT renomeada para: {new_name}")
            
            # Limpa sobras
            for extra in potential_subs[1:]:
                try: os.remove(extra)
                except: pass

    except Exception as e_ren:
        print(f"Erro ao processar legendas: {e_ren}")

    return final_video_path, project_folder