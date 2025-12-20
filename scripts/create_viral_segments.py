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

except ImportError:
    HAS_G4F = False

try:
    from llama_cpp import Llama
    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False

def clean_json_response(response_text):
    """Limpa blocos de código markdown do texto de resposta."""
    if not response_text:
        return {"segments": []}
    # Remove ```json ... ```
    # First, try to remove ```json ... ``` or just ``` ... ```
    pattern = r"```json(.*?)```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        response_text = match.group(1)
    else:
        pattern_generic = r"```(.*?)```"
        match_generic = re.search(pattern_generic, response_text, re.DOTALL)
        if match_generic:
            response_text = match_generic.group(1)
            
    # Always attempt to extract from outermost curly braces, 
    # as some models chatter before/after the code block
    start_idx = response_text.find("{")
    end_idx = response_text.rfind("}")
    
    if start_idx != -1 and end_idx != -1:
         response_text = response_text[start_idx : end_idx + 1]
    
    return json.loads(response_text.strip())


def preprocess_transcript_for_ai(segments):
    """
    Concatenates transcript segments into a single string with embedded time tags.
    Tags are inserted at the beginning (0s) and roughly every 4 seconds thereafter.
    Format: "Word word word (4s) word word..."
    """
    if not segments:
        return ""

    full_text = ""
    last_tag_time = -100  # Force first tag
    
    # Try to start with (0s) based on first segment
    first_start = segments[0].get('start', 0)
    full_text += f"({int(first_start)}s) "
    last_tag_time = first_start

    for seg in segments:
        text = seg.get('text', '').strip()
        end_time = seg.get('end', 0)
        
        # Add text
        full_text += text + " "
        
        # Add tag if ~4 seconds passed since last tag
        if end_time - last_tag_time >= 4:
            full_text += f"({int(end_time)}s) "
            last_tag_time = end_time

    return full_text.strip()

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

    # Parse Input into Segments first
    transcript_segments = []
    
    # Try to load TSV first (more reliable time)
    if os.path.exists(input_tsv):
        try:
            with open(input_tsv, 'r', encoding='utf-8') as f:
                # Skip header
                lines = f.readlines()[1:] 
                for line in lines:
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        start_ms = float(parts[0])
                        end_ms = float(parts[1])
                        text = parts[2]
                        transcript_segments.append({
                            'start': start_ms / 1000.0, 
                            'end': end_ms / 1000.0, 
                            'text': text
                        })
        except Exception as e:
            print(f"Error parsing TSV: {e}")

    # Fallback to SRT parser if TSV empty/failed
    if not transcript_segments and os.path.exists(input_srt):
         with open(input_srt, 'r', encoding='utf-8') as f:
             srt_content = f.read()
         # Simple SRT Regex Parser
         # Matches: index, time range, text
         pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*)', re.DOTALL)
         matches = pattern.findall(srt_content)
         
         def srt_time_to_seconds(t_str):
             h, m, s = t_str.replace(',', '.').split(':')
             return int(h) * 3600 + int(m) * 60 + float(s)

         for m in matches:
             start_sec = srt_time_to_seconds(m[1])
             end_sec = srt_time_to_seconds(m[2])
             text = m[3].replace('\n', ' ')
             transcript_segments.append({'start': start_sec, 'end': end_sec, 'text': text})

    if not transcript_segments:
        raise ValueError("Could not parse transcript from TSV or SRT.")

    # Generate Pre-processed Content with Time Tags
    formatted_content = preprocess_transcript_for_ai(transcript_segments)
    
    # Use formatted content for chunking
    content = formatted_content

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

    elif ai_mode == "local":
        # For local, chunk size default 3000 chars roughly matches 1024-2048 tokens depending on chars/token
        current_chunk_size = chunk_size_arg if chunk_size_arg and int(chunk_size_arg) > 0 else 3000
        # Model name is just the argument (filename)
        model_name = model_name_arg if model_name_arg else ""

    system_prompt_template = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt_template = f.read()
    else:
        # Fallback se arquivo nao existir
        print("Aviso: prompt.txt não encontrado. Usando prompt interno.")
        system_prompt_template = """You are a World-Class Viral Video Editor.
{context_instruction}
Analyze the transcript below with time tags (XXs). Find {amount} viral segments.
Constraints: {min_duration}s - {max_duration}s.
IMPORTANT: Output "Title", "Hook", and "Reasoning" in the SAME LANGUAGE as the transcript (e.g., if transcript is Portuguese, output Portuguese).
TRANSCRIPT:
{transcript_chunk}
OUTPUT JSON ONLY:
{json_template}"""


    json_template = '''
            { "segments" :
                [
                    {
                        "start_text": "Exact first 5-10 words of the segment",
                        "end_text": "Exact last 5-10 words of the segment",
                        "start_time_ref": "Value of closest (XXs) tag",
                        "title": "Viral Hook Title (Same Language as Transcript)",
                        "reasoning": "Why this is viral? Hook? Value? (Same Language as Transcript)",
                        "score": 95
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
        
        # Align End to newline to avoid cutting sentences is useless here since we process raw text line.
        # But our `formatted_content` has newlines from preprocess? Actually `preprocess_transcript_for_ai` concats with " ".
        # So we look for space.
        
        if end < content_len:
            last_space = content.rfind(' ', start, end)
            if last_space != -1 and last_space > start:
                end = last_space
        
        chunk_text = content[start:end]
        if chunk_text.strip(): # Avoid empty chunks
            chunks.append(chunk_text)
        
        if end >= content_len:
            break
            
        # Prepare start for next chunk (Backtrack by overlap)
        next_start = max(start + 1, end - overlap_size)
        
        # Align next_start to space
        safe_space = content.rfind(' ', start, next_start)
        if safe_space != -1:
            start = safe_space + 1
        else:
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

    # Initialize Local Model if needed (Once)
    local_llm_instance = None
    if ai_mode == "local":
        if not HAS_LLAMA_CPP:
            print("Error: llama-cpp-python not installed. Please install it to use Local mode.")
            return {"segments": []}
            
        models_dir = os.path.join(base_dir, 'models')
        # Check if model_name is full path or filename
        model_path = os.path.join(models_dir, model_name)
        if not os.path.exists(model_path):
             if os.path.exists(model_name): # Absolute path check
                 model_path = model_name
             else:
                 print(f"Error: Model not found at {model_path}")
                 return {"segments": []}
        
        print(f"[INFO] Loading Local Model: {os.path.basename(model_path)} (This may take a while)...")
        try:
            # Adjust n_gpu_layers=-1 for max GPU usage. n_ctx=8192 for long context.
            local_llm_instance = Llama(
                model_path=model_path,
                n_gpu_layers=-1, 
                n_ctx=8192,
                verbose=False
            )
        except Exception as e:
            print(f"Failed to load model: {e}")
            return {"segments": []}

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
            
        elif ai_mode == "local" and local_llm_instance:
            print(f"Processing chunk {i+1} with Local LLM...")
            try:
                # Use chat completion for better formatting handling
                output = local_llm_instance.create_chat_completion(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that outputs only JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=4096,
                    temperature=0.7
                )
                response_text = output['choices'][0]['message']['content']
            except Exception as e:
                print(f"Error evaluating local model: {e}")
                response_text = "{}"

        # --- Save RAW Response for Debugging ---
        try:
            raw_response_path = os.path.join(project_folder, f"response_raw_part_{i+1}.txt")
            with open(raw_response_path, "w", encoding="utf-8") as f:
                f.write(response_text)
            print(f"[DEBUG] Raw response saved to: {raw_response_path}")
        except Exception as e:
            print(f"[WARN] Failed to save raw response: {e}")
        # ----------------------------------------

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

    # --- POST-PROCESSING: Match Text to Timestamps ---
    processed_segments = []
    
    # Helper to find text in segments
    def find_timestamp_by_text(target_text, segments_list, start_search_idx=0, is_end=False):
        # Normalize target
        target_clean = "".join(target_text.lower().split())
        if not target_clean: return None, start_search_idx

        current_concat = ""
        param_idx = -1
        
        # Sliding window or simple linear scan?
        # Linear scan matches sequences of words.
        # We look for the FIRST occurrence of target_text in segments_list starting from start_search_idx
        
        # Optimization: Create a long string of remaining segments and find index, then map back?
        # Better: iterate segments.
        
        for i in range(start_search_idx, len(segments_list)):
            seg_text = segments_list[i]['text']
            # We treat this simple: check if target is basically inside this segment or spanning a few.
            # Since target is "5-10 words", it might span 2 segments.
            
            # Simple approach: Check if target (normalized) is substring of 
            # (prev + current + next) normalized.
            # This is complex. 
            
            # SIMPLER APPROACH:
            # The AI returns 'start_time_ref' (e.g., "(12s)").
            # We jump to that time in segments_list.
            # Then we look for the text in that vicinity.
            pass
        
        return None, -1

    # SIMPLIFIED MATCHING LOGIC
    # 1. Use 'start_time_ref' to find approximate index.
    # 2. Search locally for 'start_text'.
    # 3. Search forward for 'end_text'.
    
    print(f"[DEBUG] Matching {len(all_segments)} raw segments to timestamps...")
    
    for seg in all_segments:
        try:
            # 1. Parse Reference Time
            ref_time_str = seg.get('start_time_ref', '(0s)')
            ref_time_val = 0
            try:
                ref_time_val = int(re.search(r'\d+', ref_time_str).group())
            except:
                ref_time_val = 0
                
            # Find segment index closest to ref_time
            start_idx = 0
            min_diff = 999999
            for i, s in enumerate(transcript_segments):
                diff = abs(s['start'] - ref_time_val)
                if diff < min_diff:
                    min_diff = diff
                    start_idx = i
                if s['start'] > ref_time_val + 10: # Stop if we went too far
                    break
            
            # Backtrack a bit in case Ref was slightly off or text started earlier
            start_idx = max(0, start_idx - 5)
            
            # 2. Find Exact Start Text
            start_text_target = seg.get('start_text', '').lower().strip()
            # Normalize: remove punctuation
            start_text_target = re.sub(r'[^\w\s]', '', start_text_target)
            
            final_start_time = -1
            match_start_idx = -1
            
            # Search window: forward 50 segments
            search_limit = min(len(transcript_segments), start_idx + 50)
            
            for i in range(start_idx, search_limit):
                s_text = transcript_segments[i]['text'].lower()
                s_text = re.sub(r'[^\w\s]', '', s_text)
                
                # Check for partial match (start of sentence)
                if start_text_target and (start_text_target in s_text or s_text in start_text_target):
                    final_start_time = transcript_segments[i]['start']
                    match_start_idx = i
                    break
            
            # Fallback: use Ref Time if text match fails
            if final_start_time == -1:
                final_start_time = transcript_segments[start_idx]['start'] if start_idx < len(transcript_segments) else ref_time_val
                match_start_idx = start_idx

            # 3. Find End Text (starting from match_start_idx)
            end_text_target = seg.get('end_text', '').lower().strip()
            end_text_target = re.sub(r'[^\w\s]', '', end_text_target)
            
            final_end_time = -1
            
            if match_start_idx != -1:
                # Search forward for end text, extended range
                # Use a larger window but we will sanity check duration later
                search_end_limit = min(len(transcript_segments), match_start_idx + 200)
                
                for i in range(match_start_idx, search_end_limit):
                    s_text = transcript_segments[i]['text'].lower()
                    s_text = re.sub(r'[^\w\s]', '', s_text)
                    
                    if end_text_target and (end_text_target in s_text or s_text in end_text_target):
                         final_end_time = transcript_segments[i]['end']
                         break
            
            # Fallback End Time checking Duration
            if final_end_time == -1:
                 final_end_time = final_start_time + tempo_minimo # safe default
            
            # Calculate Duration
            duration = final_end_time - final_start_time
            
            # Validate Duration (Min)
            if duration < 5: 
                duration = tempo_minimo
                final_end_time = final_start_time + duration
            
            # Validate Duration (Max)
            # If AI selected start and end points that result in a huge segment, clamp it.
            if duration > tempo_maximo:
                print(f"[WARN] Segmento excede max duration ({duration:.2f}s > {tempo_maximo}s). Cortando para {tempo_maximo}s.")
                final_end_time = final_start_time + tempo_maximo
                duration = tempo_maximo

            # Construct Final Segment
            processed_segments.append({
                "title": seg.get('title', 'Viral Segment'),
                "start_time": final_start_time,
                "end_time": final_end_time,
                "hook": seg.get('title', ''), # Use title as hook text
                "reasoning": seg.get('reasoning', ''),
                "score": seg.get('score', 0),
                "duration": duration
            })

        except Exception as e:
            print(f"[WARN] Error processing segment {seg}: {e}")
            continue

    # Deduplication (Keep highest score)
    unique_segments = []
    # Sort by Score desc
    processed_segments.sort(key=lambda x: int(x.get('score', 0)), reverse=True)
    
    for candidate in processed_segments:
        is_dup = False
        for existing in unique_segments:
            s1, e1 = candidate['start_time'], candidate['end_time']
            s2, e2 = existing['start_time'], existing['end_time']
            
            overlap_start = max(s1, s2)
            overlap_end = min(e1, e2)
            
            if overlap_end > overlap_start:
                intersection = overlap_end - overlap_start
                if intersection > 5: # more than 5 seconds overlap
                    is_dup = True
                    break
        if not is_dup:
            unique_segments.append(candidate)

    all_segments = unique_segments
    print(f"[DEBUG] Finished processing. {len(all_segments)} segments valid.")
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