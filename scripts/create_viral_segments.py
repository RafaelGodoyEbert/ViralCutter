import json
import os
import re
import sys
import time

# Tenta importar bibliotecas de IA opcionalmente
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    import g4f
    HAS_G4F = True
except ImportError:
    HAS_G4F = False

def clean_json_response(response_text):
    """Limpa blocos de código markdown do texto de resposta."""
    if not response_text:
        return {"segments": []}
    # Remove ```json ... ```
    pattern = r"```json(.*?)```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        response_text = match.group(1)
    elif "```" in response_text:
         response_text = response_text.replace("```", "")
    else:
        # Fallback: Try to find the first { and last }
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")
        if start_idx != -1 and end_idx != -1:
            response_text = response_text[start_idx : end_idx + 1]
    
    return json.loads(response_text.strip())

def call_gemini(prompt, api_key, model_name='gemini-2.5-flash-lite-preview-09-2025'):
    if not HAS_GEMINI:
        raise ImportError("A biblioteca 'google-generativeai' não está instalada. Instale com: pip install google-generativeai")
    
    genai.configure(api_key=api_key)
    # Usando modelo definido na config ou o padrão
    model = genai.GenerativeModel(model_name) 
    
    max_retries = 5
    base_wait = 30

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Quota exceeded" in error_str:
                wait_time = base_wait * (attempt + 1) # Backoff default
                
                # Try to find specific wait time in error message
                match = re.search(r"retry in (\d+(\.\d+)?)s", error_str)
                if match:
                    wait_time = float(match.group(1)) + 5.0 # Add 5s buffer
                
                print(f"[429] Quota Exceeded. Waiting {wait_time:.2f}s before retry {attempt+1}/{max_retries}...", flush=True)
                time.sleep(wait_time)
                continue
            else:
                print(f"Erro na API do Gemini: {e}")
                return "{}"
    
    print("Falha após max retries no Gemini.")
    return "{}"

def call_g4f(prompt, model_name="gpt-4o-mini"):
    if not HAS_G4F:
        raise ImportError("A biblioteca 'g4f' não está instalada. Instale com: pip install g4f")
    
    try:
        # Tenta usar um provider automático
        response = g4f.ChatCompletion.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        return response
    except Exception as e:
        print(f"Erro na API do G4F: {e}")
        return "{}"

def create(num_segments, viral_mode, themes, tempo_minimo, tempo_maximo, ai_mode="manual", api_key=None, project_folder="tmp", chunk_size_arg=None, model_name_arg=None):
    quantidade_de_virals = num_segments

    # Ler transcrição
    input_tsv = os.path.join(project_folder, 'input.tsv')
    input_srt = os.path.join(project_folder, 'input.srt')
    
    # Fallback pro SRT se TSV não existir
    if not os.path.exists(input_tsv):
        print(f"Aviso: {input_tsv} não encontrado. Tentando ler do SRT raw.")
        if os.path.exists(input_srt):
             with open(input_srt, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            raise FileNotFoundError(f"Nenhum arquivo de transcrição encontrado em {project_folder}")
    else:
        with open(input_tsv, 'r', encoding='utf-8') as f:
            content = f.read()

    # Load Config and Prompt
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, 'api_config.json')
    prompt_path = os.path.join(base_dir, 'prompt.txt')

    # Default Config
    config = {
        "selected_api": "gemini",
        "gemini": {
            "api_key": "",
            "model": "gemini-2.5-flash-lite-preview-09-2025",
            "chunk_size": 15000
        },
        "g4f": {
            "model": "gpt-4o-mini",
            "chunk_size": 2000
        }
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # Merge simples
                if "gemini" in loaded_config: config["gemini"].update(loaded_config["gemini"])
                if "g4f" in loaded_config: config["g4f"].update(loaded_config["g4f"])
                if "selected_api" in loaded_config: config["selected_api"] = loaded_config["selected_api"]
        except Exception as e:
            print(f"Erro ao ler api_config.json: {e}. Usando padrões.")

    # Configurar variaveis baseadas no ai_mode
    current_chunk_size = 15000 # default fallback
    model_name = ""
    
    if ai_mode == "gemini":
        cfg_chunk = config["gemini"].get("chunk_size", 15000)
        current_chunk_size = chunk_size_arg if chunk_size_arg and int(chunk_size_arg) > 0 else cfg_chunk
        
        cfg_model = config["gemini"].get("model", "gemini-2.5-flash-lite-preview-09-2025")
        model_name = model_name_arg if model_name_arg else cfg_model
        
        if not api_key: # Se não veio por argumento, tenta do config
            api_key = config["gemini"].get("api_key", "")
            
    elif ai_mode == "g4f":
        cfg_chunk = config["g4f"].get("chunk_size", 2000)
        current_chunk_size = chunk_size_arg if chunk_size_arg and int(chunk_size_arg) > 0 else cfg_chunk
        
        cfg_model = config["g4f"].get("model", "gpt-4o-mini")
        model_name = model_name_arg if model_name_arg else cfg_model

    system_prompt_template = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt_template = f.read()
    else:
        # Fallback se arquivo nao existir
        print("Aviso: prompt.txt não encontrado. Usando prompt interno.")
        system_prompt_template = """You are a Viral Segment Identifier. 
{context_instruction}
Given the following video transcript chunk, {virality_instruction}.
CONSTRAINTS:
- Each segment duration: {min_duration}s to {max_duration}s.
- Cuts MUST MAKE SENSE contextually.
- RETURN ONLY VALID JSON.

TRANSCRIPT CHUNK:
{transcript_chunk}

OUTPUT FORMAT:
{json_template}"""


    json_template = '''
            { "segments" :
                [
                    {
                        "title": "Suggested Viral Title on same language of tsv",
                        "start_time": number,
                        "end_time": number,
                        "hook": "On-screen hook text that grabs attention",
                        "duration": 0,
                        "score": 0  # Probability of going viral (0-100)
                    }
                ]
            }
        '''

    # Split content into chunks
    # Split content into chunks with OVERLAP
    chunk_size = int(current_chunk_size)
    
    # Define overlap size (e.g. 10% of chunk size or min 1000 chars)
    overlap_size = max(1000, int(chunk_size * 0.1))
    
    chunks = []
    start = 0
    content_len = len(content)

    print(f"[DEBUG] Chunking content (Size: {content_len}) with Chunk Size: {chunk_size} and Overlap: {overlap_size}")

    while start < content_len:
        end = min(start + chunk_size, content_len)
        
        # Align End to newline to avoid cutting sentences
        if end < content_len:
            last_newline = content.rfind('\n', start, end)
            if last_newline != -1 and last_newline > start:
                end = last_newline
        
        chunk_text = content[start:end]
        if chunk_text.strip(): # Avoid empty chunks
            chunks.append(chunk_text)
        
        if end >= content_len:
            break
            
        # Prepare start for next chunk (Backtrack by overlap)
        next_start = max(start + 1, end - overlap_size)
        
        # Align next_start to a newline for clean start
        # Find newline strictly before next_start? Or nearest?
        # Safe bet: Find last newline before 'next_start' but after 'start'
        safe_newline = content.rfind('\n', start, next_start)
        if safe_newline != -1:
            start = safe_newline + 1
        else:
            # If no newline found (huge block of text), just use next_start
            start = next_start

    if viral_mode:
        virality_instruction = f"""analyze the segment for potential virality and identify {quantidade_de_virals} most viral segments from the transcript"""
    else:
        virality_instruction = f"""analyze the segment for potential virality and identify {quantidade_de_virals} the best parts based on the list of themes {themes}."""

    output_texts = []
    for i, chunk in enumerate(chunks):
        context_instruction = ""
        if len(chunks) > 1:
            context_instruction = f"Part {i+1} of {len(chunks)}. "
        
        # Preencher o template
        try:
            prompt = system_prompt_template.format(
                context_instruction=context_instruction,
                virality_instruction=virality_instruction,
                min_duration=tempo_minimo,
                max_duration=tempo_maximo,
                transcript_chunk=chunk,
                json_template=json_template,
                amount=quantidade_de_virals # Caso o user use {amount} no txt
            )
        except KeyError as e:
            # Fallback se o user bagunçou o txt e esqueceu chaves ou colocou chaves erradas
            # Tenta um replace manual basico ou avisa erro, mas ideal é não quebrar.
            # Vamos usar replace seguro
            prompt = system_prompt_template
            prompt = prompt.replace("{context_instruction}", context_instruction)
            prompt = prompt.replace("{virality_instruction}", virality_instruction)
            prompt = prompt.replace("{min_duration}", str(tempo_minimo))
            prompt = prompt.replace("{max_duration}", str(tempo_maximo))
            prompt = prompt.replace("{transcript_chunk}", chunk)
            prompt = prompt.replace("{json_template}", json_template)
            prompt = prompt.replace("{amount}", str(quantidade_de_virals))

        output_texts.append(prompt)

    # --- Save Full Prompt for Reference ---
    try:
        full_prompt_path = os.path.join(project_folder, "prompt_full.txt")
        # Prepare full prompt using replace to be safe
        full_prompt = system_prompt_template
        full_prompt = full_prompt.replace("{context_instruction}", "Full Video Transcript Analysis")
        full_prompt = full_prompt.replace("{virality_instruction}", virality_instruction)
        full_prompt = full_prompt.replace("{min_duration}", str(tempo_minimo))
        full_prompt = full_prompt.replace("{max_duration}", str(tempo_maximo))
        full_prompt = full_prompt.replace("{transcript_chunk}", content) # Full Content
        full_prompt = full_prompt.replace("{json_template}", json_template)
        full_prompt = full_prompt.replace("{amount}", str(quantidade_de_virals))
        
        with open(full_prompt_path, "w", encoding="utf-8") as f:
            f.write(full_prompt)
        # print(f"[INFO] Full reference prompt saved to: {full_prompt_path}")
    except Exception as e:
        print(f"[WARN] Could not save prompt_full.txt: {e}")
    # -------------------------------------

    all_segments = []

    print(f"Processando {len(output_texts)} chunks usando modo: {ai_mode.upper()}")

    for i, prompt in enumerate(output_texts):
        response_text = ""
        
        # Always save prompt to file (Manual, Gemini, or G4F)
        manual_prompt_path = os.path.join(project_folder, f"prompt_part_{i+1}.txt")
        try:
            with open(manual_prompt_path, "w", encoding="utf-8") as f:
                f.write(prompt)
        except Exception as e:
            print(f"[ERRO] Falha ao salvar prompt.txt: {e}")
        
        if ai_mode == "manual":
            print(f"\n[INFO] O prompt foi salvo em: {manual_prompt_path}")
            
            print("\n" + "="*60)
            print(f"CHUNK {i+1}/{len(output_texts)}")
            print("="*60)
            print("COPIE O PROMPT ABAIXO (OU DO ARQUIVO GERADO) E COLE NA SUA IA PREFERIDA:")
            print("-" * 20)
            print(prompt)
            print("-" * 20)
            print("="*60)
            print("Cole o JSON de resposta abaixo e pressione ENTER.")
            print("Dica: Se o JSON tiver múltiplas linhas, tente colar tudo de uma vez ou minificado.")
            print("Se preferir, digite 'file' para ler de um arquivo 'tmp/response.json'.")
            
            user_input = input("JSON ou 'file': ")
            
            if user_input.lower() == 'file':
                try:
                    response_json_path = os.path.join(project_folder, 'response.json')
                    with open(response_json_path, 'r', encoding='utf-8') as rf:
                        response_text = rf.read()
                except FileNotFoundError:
                    print(f"Arquivo {response_json_path} não encontrado.")
            else:
                response_text = user_input
                # Tenta ler mais linhas se parecer incompleto (bruteforce simples)
                if response_text.strip().startswith("{") and not response_text.strip().endswith("}"):
                    print("Parece incompleto. Cole o resto e dê Enter (ou Ctrl+C para cancelar):")
                    try:
                        rest = sys.stdin.read() # Isso pode travar no Windows sem EOF explícito
                        response_text += rest
                    except:
                        pass

        elif ai_mode == "gemini":
            print(f"Enviando chunk {i+1} para o Gemini (Model: {model_name})...")
            response_text = call_gemini(prompt, api_key, model_name=model_name)
        
        elif ai_mode == "g4f":
            print(f"Enviando chunk {i+1} para o G4F (Model: {model_name})...")
            response_text = call_g4f(prompt, model_name=model_name)

        # Processar resposta
        try:
            data = clean_json_response(response_text)
            chunk_segments = data.get("segments", [])
            print(f"Encontrados {len(chunk_segments)} segmentos neste chunk.")
            all_segments.extend(chunk_segments)
        except json.JSONDecodeError:
            print(f"Erro: Resposta inválida (não é JSON válida).")
            print(f"Conteúdo recebido (primeiros 100 chars): {response_text[:100]}...")
        except Exception as e:
            print(f"Erro desconhecido ao processar chunk: {e}")

    # Sort segments by score (descending) to get the best ones globally
    try:
        all_segments.sort(key=lambda x: int(x.get('score', 0)), reverse=True)
    except:
        pass # If scores are not valid integers, skip sorting or rely on order

    # --- DEDUPLICATION LOGIC ---
    # Merge overlapping segments. Prioritize higher score.
    unique_segments = []
    
    def check_overlap(seg1, seg2):
        # Convert times to float just in case
        try:
            s1, e1 = float(seg1.get('start_time', 0)), float(seg1.get('end_time', 0))
            s2, e2 = float(seg2.get('start_time', 0)), float(seg2.get('end_time', 0))
            
            # Calculate intersection
            start_max = max(s1, s2)
            end_min = min(e1, e2)
            
            if end_min > start_max:
                intersection = end_min - start_max
                duration1 = e1 - s1
                duration2 = e2 - s2
                # If intersection covers > 30% of the smaller segment, consider it a duplicate
                min_dur = min(duration1, duration2)
                if min_dur > 0 and (intersection / min_dur) > 0.3:
                    return True
            return False
        except:
            return False

    print(f"[DEBUG] Starting Deduplication on {len(all_segments)} raw segments...")
    
    for candidate in all_segments:
        is_duplicate = False
        for accepted in unique_segments:
            if check_overlap(candidate, accepted):
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_segments.append(candidate)
            
    print(f"[DEBUG] Deduplication finished. Kept {len(unique_segments)} unique segments.")
    all_segments = unique_segments
    # ---------------------------

    # Limit to the requested number of segments
    if quantidade_de_virals and len(all_segments) > quantidade_de_virals:
        print(f"Filtrando os top {quantidade_de_virals} segmentos de {len(all_segments)} candidatos encontrados nos chunks.")
        all_segments = all_segments[:quantidade_de_virals]

    final_result = {"segments": all_segments}
    
    # Validação básica de duração nos resultados (opcional, mas bom pra evitar erros no ffmpeg)
    # Convertendo milliseconds pra int se necessário, garantindo sanidade
    validated_segments = []
    for seg in final_result['segments']:
        # Garante start_time
        if 'start_time' in seg:
             # Deixa passar, cut_segments lida com int/str conversion
             validated_segments.append(seg)
    
    final_result['segments'] = validated_segments
    
    return final_result