import os
import sys
import torch
import time
import whisperx
import gc
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
        # Motivo: O pyannote carrega muitos checkpoints antigos que não são compatíveis com weights_only=True
        # Forçamos False incondicionalmente, ignorando o que for passado.
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

def transcribe(input_file, model_name='large-v3', project_folder='tmp'):
    print(i18n(f"Iniciando transcrição de {input_file}..."))
    
    # Diagnóstico de Ambiente
    print(f"DEBUG: Python: {sys.executable}")
    print(f"DEBUG: Torch: {torch.__version__}")
    
    start_time = time.time()
    
    # Se project_folder for None, tenta inferir do input_file ou usa tmp
    if project_folder is None:
        project_folder = os.path.dirname(input_file)
        if not project_folder:
            project_folder = 'tmp'

    output_folder = project_folder
    os.makedirs(output_folder, exist_ok=True)
    
    # O input_file pode ser absoluto, então basename está correto
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    srt_file = os.path.join(output_folder, f"{base_name}.srt")
    tsv_file = os.path.join(output_folder, f"{base_name}.tsv")
    json_file = os.path.join(output_folder, f"{base_name}.json")

    # Verifica se os arquivos já existem
    if os.path.exists(srt_file) and os.path.exists(tsv_file) and os.path.exists(json_file):
        print(f"Os arquivos SRT, TSV e JSON já existem. Pulando a transcrição.")
        return srt_file, tsv_file

    # ... (Configuração e Transcrição) ...

    # Configuração de Dispositivo
    # Se CUDA estiver disponível no ambiente ATUAL, usamos.
    # Forçamos uma nova verificação limpa.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"DEBUG: Usando dispositivo: {device}")
    
    # Parâmetros de computação
    # float16 é melhor pra GPU, mas se der erro podemos fallback pra int8 ou float32
    compute_type = "float16" if device == "cuda" else "float32"

    try:
        # Patch para erro de pickle/unpickle se necessário
        apply_safe_globals_hack()

        # 1. Carregar Modelo
        print(f"Carregando modelo {model_name}...")
        model = whisperx.load_model(
            model_name, 
            device, 
            compute_type=compute_type, 
            asr_options={
                "hotwords": None,
            }
        )

        # 2. Carregar Áudio
        print(f"Carregando áudio: {input_file}")
        audio = whisperx.load_audio(input_file)

        # 3. Transcrever
        print("Realizando transcrição (WhisperX)...")
        result = model.transcribe(
            audio, 
            batch_size=16, # Batch size ajustável
            chunk_size=10
        )
        
        # 3.5 Alinhar (Critical for word-level timestamps)
        print("Alinhando transcrição para obter timestamps precisos...")
        try:
            detected_language = result["language"]
            model_a, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
            
            # Restaurar a chave 'language' que o align remove (necessária para os writers)
            result["language"] = detected_language
            
            # Limpar modelo de alinhamento da memória
            if device == "cuda":
                 del model_a
                 torch.cuda.empty_cache()
                 
        except Exception as e:
            print(f"Erro durante alinhamento: {e}. Continuando com transcrição bruta (pode afetar legendas dinâmicas).")

        # 4. Salvar Resultados
        print("Salvando resultados...")
        
        # WhisperX retorna um dicionário com 'segments'.
        # Precisamos converter para o formato que a ferramenta 'whisperx' CLI salva,
        # ou usar as funções de writer do próprio whisperx se disponíveis publicamente.
        # O whisperx.utils.get_writer é o caminho correto.
        
        from whisperx.utils import get_writer
        
        # Cria writers para SRT e TSV
        # O argumento 'output_dir' define onde salvar
        save_options = {
            "highlight_words": False,
            "max_line_count": None,
            "max_line_width": None
        }
        
        # Escreve SRT
        writer_srt = get_writer("srt", output_folder)
        writer_srt(result, input_file, save_options)
        
        # Escreve TSV
        writer_tsv = get_writer("tsv", output_folder)
        writer_tsv(result, input_file, save_options)
        
        # Escreve JSON (Novo)
        writer_json = get_writer("json", output_folder)
        writer_json(result, input_file, save_options)
        
        # Limpeza de memória VRAM
        if device == "cuda":
            del model
            gc.collect()
            torch.cuda.empty_cache()

        end_time = time.time()
        elapsed_time = end_time - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        print(f"Transcrição concluída em {minutes}m {seconds}s.")

    except Exception as e:
        print(f"ERRO CRÍTICO na transcrição: {e}")
        import traceback
        traceback.print_exc()
        raise

    # Verificação Final
    if not os.path.exists(srt_file):
        print(f"AVISO: Arquivo SRT {srt_file} não encontrado após execução.")
    
    return srt_file, tsv_file
