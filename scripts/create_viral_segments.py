import json
import os
import re

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
    
    return json.loads(response_text.strip())

def call_gemini(prompt, api_key, model_name='gemini-2.5-flash-lite-preview-09-2025'):
    if not HAS_GEMINI:
        raise ImportError("A biblioteca 'google-generativeai' não está instalada. Instale com: pip install google-generativeai")
    
    genai.configure(api_key=api_key)
    # Usando modelo definido na config ou o padrão
    model = genai.GenerativeModel(model_name) 
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erro na API do Gemini: {e}")
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
                        "title": "Suggested Viral Title",
                        "start_time": number,
                        "end_time": number,
                        "description": "Description of the text",
                        "duration": 0,
                        "score": 0  # Probability of going viral (0-100)
                    }
                ]
            }
        '''

    # Split content into chunks
    chunk_size = int(current_chunk_size)
    chunks = []
    start = 0

    while start < len(content):
        end = min(start + chunk_size, len(content))
        if end < len(content):
            end = content.rfind('\n', start, end)
            if end == -1:
                end = start + chunk_size
        chunks.append(content[start:end])
        start = end

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

    all_segments = []

    print(f"Processando {len(output_texts)} chunks usando modo: {ai_mode.upper()}")

    for i, prompt in enumerate(output_texts):
        response_text = ""
        
        # Always save prompt to file (Manual, Gemini, or G4F)
        manual_prompt_path = os.path.join(project_folder, "prompt.txt")
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

    # Retorna o dicionário consolidado
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