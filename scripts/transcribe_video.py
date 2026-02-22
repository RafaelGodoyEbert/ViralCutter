import os
import sys
import torch
import time
import whisperx
import gc
import re
import glob
from i18n.i18n import I18nAuto

i18n = I18nAuto()

def apply_safe_globals_hack():
    """
    Workaround for 'Weights only load failed' error in newer PyTorch versions.
    We first try to add safe globals. If that's not enough/fails, we monkeypatch torch.load.
    """
    try:
        import omegaconf
        if hasattr(torch.serialization, 'add_safe_globals'):
            torch.serialization.add_safe_globals([
                omegaconf.listconfig.ListConfig,
                omegaconf.dictconfig.DictConfig,
                omegaconf.base.ContainerMetadata,
                omegaconf.base.Node
            ])
            print("Aplicado patch de segurança para globals do Omegaconf.")
            
        # Monkeypatch agressivo para garantir compatibilidade com Pyannote/WhisperX antigos
        original_load = torch.load
        
        def safe_load(*args, **kwargs):
            kwargs['weights_only'] = False
            return original_load(*args, **kwargs)
            
        torch.load = safe_load
        print("Aplicado monkeypatch em torch.load para forçar weights_only=False.")
        
    except ImportError:
        pass
    except Exception as e:
        print(f"Aviso ao tentar aplicar patch de globals: {e}")

    try:
        import torchaudio
        if not hasattr(torchaudio, 'list_audio_backends'):
            torchaudio.list_audio_backends = lambda: []
            print("Aplicado monkeypatch em torchaudio.list_audio_backends para PyTorch >= 2.4.")
    except Exception as e:
        pass

def parse_srt(srt_path):
    """
    Parses an SRT file into a list of segments expected by WhisperX alignment.
    [{'start': float, 'end': float, 'text': str}, ...]
    """
    print(f"Parsing SRT: {srt_path}")
    segments = []
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        content = content.replace('\r\n', '\n')
        blocks = content.strip().split('\n\n')
        
        def time_to_seconds(t_str):
            # SRT: 00:00:00,000
            t_str = t_str.replace(',', '.')
            parts = t_str.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s)
            return 0.0

        for block in blocks:
            lines = block.split('\n')
            # Busca linha de tempo
            for i, line in enumerate(lines):
                if '-->' in line:
                    start_str, end_str = line.split(' --> ')
                    text_lines = lines[i+1:]
                    text = " ".join(text_lines).strip()
                    text = re.sub(r'<[^>]+>', '', text) # Remove tags
                    
                    if text:
                        start = time_to_seconds(start_str.strip())
                        end = time_to_seconds(end_str.strip())
                        segments.append({
                            "start": start,
                            "end": end,
                            "text": text
                        })
                    break
    except Exception as e:
        print(f"Error parsing SRT {srt_path}: {e}")
        return None
    return segments

def parse_vtt(vtt_path):
    """
    Parses a VTT file (WebVTT) into valid segments for WhisperX.
    """
    print(f"Parsing VTT: {vtt_path}")
    segments = []
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        def vtt_time_to_seconds(t_str):
            # VTT: 00:00:00.000 or 00:00.000
            t_str = t_str.strip()
            parts = t_str.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s)
            return 0.0

        current_entry = {"text": []}
        
        for line in lines:
            line = line.strip()
            if not line:
                # Fim de bloco, salva se tiver tempo e texto
                if "start" in current_entry and current_entry["text"]:
                    full_text = " ".join(current_entry["text"]).strip()
                    # Limpeza extra VTT
                    full_text = re.sub(r'<[^>]+>', '', full_text)
                    full_text = re.sub(r'&[^;]+;', '', full_text)
                    
                    if full_text:
                        segments.append({
                            "start": current_entry["start"],
                            "end": current_entry["end"],
                            "text": full_text
                        })
                current_entry = {"text": []}
                continue
            
            if line.startswith("WEBVTT") or line.startswith("X-TIMESTAMP-MAP") or line.startswith("NOTE"):
                continue

            # Timestamp line: 00:00:05.000 --> 00:00:10.000 (pode ter settings depois)
            if "-->" in line:
                times = line.split("-->")
                start_str = times[0].strip()
                end_str = times[1].strip().split(" ")[0] # remove settings
                current_entry["start"] = vtt_time_to_seconds(start_str)
                current_entry["end"] = vtt_time_to_seconds(end_str)
            else:
                # É texto (se já tivermos timestamps)
                if "start" in current_entry:
                     current_entry["text"].append(line)
                     
        # Salva ultimo bloco se existir
        if "start" in current_entry and current_entry["text"]:
            full_text = " ".join(current_entry["text"]).strip()
            full_text = re.sub(r'<[^>]+>', '', full_text)
            if full_text:
                segments.append({
                    "start": current_entry["start"],
                    "end": current_entry["end"],
                    "text": full_text
                })

    except Exception as e:
        print(f"Error parsing VTT {vtt_path}: {e}")
        return None
    return segments

def transcribe(input_file, model_name='large-v3', project_folder='tmp'):
    print(i18n(f"Iniciando transcrição de {input_file}..."))
    
    # Diagnóstico de Ambiente
    print(f"DEBUG: Python: {sys.executable}")
    print(f"DEBUG: Torch: {torch.__version__}")
    
    start_time = time.time()
    
    if project_folder is None:
        project_folder = os.path.dirname(input_file)
        if not project_folder:
            project_folder = 'tmp'

    output_folder = project_folder
    os.makedirs(output_folder, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    srt_file = os.path.join(output_folder, f"{base_name}.srt")
    tsv_file = os.path.join(output_folder, f"{base_name}.tsv")
    json_file = os.path.join(output_folder, f"{base_name}.json")

    # Verifica se os arquivos já existem
    if os.path.exists(srt_file) and os.path.exists(tsv_file) and os.path.exists(json_file):
        print(f"Os arquivos SRT, TSV e JSON já existem. Pulando a transcrição.")
        return srt_file, tsv_file

    # Device Setup
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"DEBUG: Usando dispositivo: {device}")
    compute_type = "float16" if device == "cuda" else "float32"

    try:
        apply_safe_globals_hack()
        
        # 1. Carregar Áudio (sempre necessário)
        print(f"Carregando áudio: {input_file}")
        audio = whisperx.load_audio(input_file)
        
        # 2. Verificar se existem legendas baixadas para Alignment Only
        # Procurar por *.srt E *.vtt na pasta que comecem com input (ou o nome base)
        if os.path.exists(os.path.join(output_folder, "input.srt")):
            potential_subs = [os.path.join(output_folder, "input.srt")]
        elif os.path.exists(os.path.join(output_folder, "input.vtt")):
            potential_subs = [os.path.join(output_folder, "input.vtt")]
        else:
            potential_subs = []
        
        start_segments = None
        alignment_only = False
        
        # Default blind guess if we have no info
        detected_language = "en" 

        if potential_subs:
            sub_path = potential_subs[0]
            print(f"Usando legenda fornecida: {sub_path}")
            
            if sub_path.endswith('.srt'):
                parsed = parse_srt(sub_path)
            elif sub_path.endswith('.vtt'):
                parsed = parse_vtt(sub_path)
            else:
                parsed = None

            if parsed and len(parsed) > 0:
                start_segments = parsed
                alignment_only = True
                
                # Forçar EN conforme solicitado pelo usuário para alinhamento
                detected_language = 'en'
                print(f"Idioma forçado para alinhamento: {detected_language}")
                
                print("--- MODO ALINHAMENTO RÁPIDO ATIVADO ---")
        
        result = None
        
        if alignment_only and start_segments:
            # Pular Transcrição, ir direto para Alinhamento
            print("--- MODO ALINHAMENTO RÁPIDO ATIVADO ---")
            # Estrutura que o align espera: {'segments': [...], 'language': ...}
            # Mas o align recebe segments como lista.
            pass 
        else:
            # 3. Transcrever (Caminho Normal)
            print("Nenhuma legenda válida encontrada. Realizando transcrição completa (WhisperX)...")
            print(f"Carregando modelo {model_name}...")
            model = whisperx.load_model(
                model_name, 
                device, 
                compute_type=compute_type,
                asr_options={"hotwords": None}
            )

            result = model.transcribe(
                audio, 
                batch_size=16, 
                chunk_size=10
            )
            
            detected_language = result["language"]
            start_segments = result["segments"]
            
            # Limpar modelo de transcrição
            if device == "cuda":
                del model
                gc.collect()
                torch.cuda.empty_cache()

        # 4. Alinhar (Sempre executado, seja com subs parsed ou transcritos)
        print(f"Alinhando transcrição (Idioma: {detected_language}) para obter timestamps precisos...")
        # Usa o modelo específico solicitado pelo usuário: WAV2VEC2_ASR_LARGE_LV60K_960H
        # Mas o whisperx.load_align_model escolhe automaticamente baseado na linguagem.
        # Se for inglês, ele usa wav2vec2-large-960h-lv60-self geralmente.
        # Não podemos forçar facilmente o modelo exato sem hackear o whisperx, mas o padrão é bom.
        
        try:
            model_a, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
            
            aligned_result = whisperx.align(start_segments, model_a, metadata, audio, device, return_char_alignments=False)
            
            # aligned_result agora contém "segments" com word timestamps
            result = aligned_result
            result["language"] = detected_language
            
            if device == "cuda":
                 del model_a
                 torch.cuda.empty_cache()
                 
        except Exception as e:
            print(f"Erro durante alinhamento: {e}. ")
            if alignment_only:
                 print("Falha crítica no alinhamento de legendas externas. Abortando usage de legendas externas.")
                 # Opcional: Fallback para transcrição normal se falhar? Seria complexo aqui pois já limpamos memória.
                 # Vamos apenas salvar o que temos (timestamps da legenda original podem não bater com áudio perfeitamente se não alinhar)
                 result = {"segments": start_segments, "language": detected_language}
            else:
                 print("Continuando com transcrição bruta.")

        # 5. Salvar Resultados
        print("Salvando resultados...")
        from whisperx.utils import get_writer
        
        save_options = {
            "highlight_words": False,
            "max_line_count": None,
            "max_line_width": None
        }
        
        # Se veio do alignment_only, result é {'segments': [...], ...}
        # Se o alinhamento falhou, result tem segments originais.
        
        # WhisperX writers esperam um dicionário result com chaves 'segments', 'language'.
        
        writer_srt = get_writer("srt", output_folder)
        writer_srt(result, input_file, save_options)
        
        writer_tsv = get_writer("tsv", output_folder)
        writer_tsv(result, input_file, save_options)
        
        writer_json = get_writer("json", output_folder)
        writer_json(result, input_file, save_options)
        
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"Processamento concluído em {int(elapsed//60)}m {int(elapsed%60)}s.")

    except Exception as e:
        print(f"ERRO CRÍTICO na transcrição: {e}")
        import traceback
        traceback.print_exc()
        raise

    if not os.path.exists(srt_file):
        print(f"AVISO: Arquivo SRT {srt_file} não encontrado após execução.")
    
    return srt_file, tsv_file
