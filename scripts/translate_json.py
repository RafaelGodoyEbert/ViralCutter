import os
import json
import asyncio
from pathlib import Path
import tqdm.asyncio
from deep_translator import GoogleTranslator

# Lista de idiomas alvo
target_languages = ['en']

# Dicionário de substituições por idioma
substituicoes_por_idioma = {
    'en': {
        # 'Original': 'Translation'
    },
}

# Configurações de tradução
sentence_endings = ['.', '!', '?', ')', 'よ', 'ね', 'の', 'さ', 'ぞ', 'な', 'か', '！', '。', '」', '…']
separator = " ◌ "
separator_unjoin = separator.replace(' ', '')
chunk_max_chars = 4999

def substituir_texto(text, substituicoes):
    """Função para substituir texto."""
    for old, new in substituicoes.items():
        text = text.replace(old, new)
    return text

async def translate_chunk(index, chunk, target_lang):
    while True:
        try:
            translator = GoogleTranslator(source='auto', target=target_lang)
            translated_chunk = await asyncio.get_event_loop().run_in_executor(None, translator.translate, chunk)
            await asyncio.sleep(0)

            if translated_chunk is None or len(translated_chunk.replace(separator.strip(), '').split()) == 0:
                return chunk

            return translated_chunk
        except Exception as e:
            print(f"\r[chunk {index}]: Exception: {e.__doc__} Retrying in 30 seconds...", flush=True)
            await asyncio.sleep(30)

def join_sentences(texts, max_chars):
    joined_texts = []
    current_chunk = ""

    for text in texts:
        if not text or text is None:
            text = 'ㅤ'

        if len(current_chunk) + len(text) + len(separator) <= max_chars:
            current_chunk += text + separator
            if any(text.endswith(ending) for ending in sentence_endings):
                joined_texts.append(current_chunk)
                current_chunk = ""
        else:
            if current_chunk:
                joined_texts.append(current_chunk)
                current_chunk = ""
            if len(current_chunk) + len(text) + len(separator) <= max_chars:
                current_chunk += text + separator
            else:
                end_index = text.rfind(' ', 0, max_chars - (1 + len(separator)))
                if end_index == - (1 + len(separator)):
                    end_index = max_chars - (1 + len(separator))
                joined_texts.append((text[:end_index] + '…' + separator)[:max_chars])

    if current_chunk:
        joined_texts.append(current_chunk)

    return joined_texts

def unjoin_sentences(original_sentence: str, modified_sentence: str, separator: str):
    if original_sentence is None:
        return ' '

    original_texts = original_sentence.split(separator)
    original_texts = [s.strip() for s in original_texts if s.strip()]

    if modified_sentence is None:
        return original_texts or ' '

    modified_sentence = modified_sentence.replace(f"{separator_unjoin} ", f"{separator_unjoin}").replace(f" {separator_unjoin}", f"{separator_unjoin}").replace(
        f"{separator_unjoin}.", f".{separator_unjoin}").replace(f"{separator_unjoin},", f",{separator_unjoin}")

    modified_texts = modified_sentence.split(separator_unjoin)
    modified_texts = [s.strip() for s in modified_texts if s.strip()]

    if original_texts == "..." or original_texts == "…":
        return original_texts

    if len(original_texts) == len(modified_texts):
        return modified_texts

    original_word_count = sum(len(text.split()) for text in original_texts)
    modified_word_count = len(' '.join(modified_texts).split())
    
    if original_word_count == 0 or modified_word_count == 0:
        return original_sentence.replace(separator, ' ').strip()

    modified_words_proportion = modified_word_count / original_word_count
    modified_words = ' '.join(modified_texts).split()

    new_modified_texts = []
    current_index = 0

    for original_text in original_texts:
        num_words = max(1, int(round(len(original_text.split()) * modified_words_proportion)))
        text_words = modified_words[current_index:current_index + num_words]
        new_modified_texts.append(' '.join(text_words))
        current_index += num_words

    if current_index < len(modified_words):
        new_modified_texts[-1] += ' ' + ' '.join(modified_words[current_index:])

    return new_modified_texts or original_texts or ' '

def adjust_segments(segments):
    for i in range(len(segments)):
        current_segment = segments[i]
        next_segment = segments[i + 1] if i < len(segments) - 1 else None
        
        # Divide o texto em palavras
        text_words = current_segment['text'].split()
        
        # Ajusta as palavras do segmento atual
        current_segment['words'] = [
            {
                'word': word,
                'start': current_segment['start'] + (idx * (current_segment['end'] - current_segment['start']) / len(text_words)),
                'end': current_segment['start'] + ((idx + 1) * (current_segment['end'] - current_segment['start']) / len(text_words)),
                'score': 1.0  # Mantemos o score como 1.0 já que não temos informações precisas
            }
            for idx, word in enumerate(text_words)
        ]
        
        # Ajusta o fim da última palavra do segmento atual
        if current_segment['words']:
            last_word = current_segment['words'][-1]
            if next_segment:
                # Estende até o início do próximo segmento ou até 2 segundos, o que ocorrer primeiro
                extended_end = min(next_segment['start'], last_word['start'] + 2)
            else:
                # Se for o último segmento, estende por até 2 segundos
                extended_end = min(current_segment['end'] + 2, last_word['start'] + 2)
            
            last_word['end'] = extended_end
            current_segment['end'] = extended_end
        
        # Ajusta o início do próximo segmento se necessário
        if next_segment and next_segment['words']:
            next_segment['words'][0]['start'] = next_segment['start']
    
    return segments

async def translate_json_file(json_file_path: Path, translated_json_path: Path, target_lang):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    segments = data['segments']
    texts_to_translate = [segment['text'] for segment in segments if segment['text']]
    words_to_translate = [word['word'] for segment in segments for word in segment['words']]

    all_texts = texts_to_translate + words_to_translate
    chunks = join_sentences(all_texts, chunk_max_chars)
    translated_chunks = [None] * len(chunks)

    tasks = []
    semaphore = asyncio.Semaphore(7)

    async def translate_async():
        async def run_translate(index, chunk, lang):
            while True:
                try:
                    async with semaphore:
                        result = await asyncio.wait_for(translate_chunk(index, chunk, lang), 120)
                    translated_chunks[index] = result
                    break
                except Exception:
                    await asyncio.sleep(3)

        for index, chunk in enumerate(chunks):
            task = asyncio.create_task(run_translate(index, chunk, target_lang))
            tasks.append(task)

        for tsk in tqdm.asyncio.tqdm_asyncio.as_completed(tasks, total=len(tasks), desc="Translating", unit="chunks", unit_scale=False, leave=True, bar_format="{desc} {percentage:3.0f}% | {n_fmt}/{total_fmt} | ETA: {remaining} | ⏱: {elapsed}"):
            await tsk

    await translate_async()

    print('Processing translation...', end='')

    unjoined_texts = [unjoin_sentences(chunk, translated_chunks[i], separator_unjoin) for i, chunk in enumerate(chunks)]
    unjoined_texts = [text for sublist in unjoined_texts for text in sublist if text]

    translated_texts = unjoined_texts[:len(texts_to_translate)]
    translated_words = unjoined_texts[len(texts_to_translate):]

    word_index = 0
    text_index = 0
    for segment in segments:
        if segment['text']:
            segment['text'] = translated_texts[text_index] if text_index < len(translated_texts) else segment['text']
            text_index += 1
        for word in segment['words']:
            if word_index < len(translated_words):
                word['word'] = translated_words[word_index]
                word_index += 1
            else:
                print(f"\nWarning: Not enough translated words. Keeping original word: {word['word']}")

    # Ajusta os segmentos após a tradução
    segments = adjust_segments(segments)

    data['segments'] = segments

    os.makedirs(translated_json_path.parent, exist_ok=True)
    with open(translated_json_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print('\r                         ', end='\r')

    return data
    
async def main():
    folder_path = './JSON/'

    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            base_name = os.path.splitext(filename)[0]

            for lang in target_languages:
                output_filename = f'{base_name}_{lang}.json'
                output_file_path = os.path.join(folder_path, output_filename)
                
                if not os.path.exists(output_file_path):
                    print(f'Traduzindo para {lang}: {filename}')
                    translated_data = await translate_json_file(Path(os.path.join(folder_path, filename)), Path(output_file_path), lang)
                    
                    if lang in substituicoes_por_idioma:
                        for segment in translated_data['segments']:
                            segment['text'] = substituir_texto(segment['text'], substituicoes_por_idioma[lang])
                            for word in segment['words']:
                                word['word'] = substituir_texto(word['word'], substituicoes_por_idioma[lang])
                    
                    with open(output_file_path, 'w', encoding='utf-8') as file:
                        json.dump(translated_data, file, ensure_ascii=False, indent=2)

            # Realiza as substituições no arquivo original JSON após todas as traduções
            original_file_path = os.path.join(folder_path, filename)
            with open(original_file_path, 'r', encoding='utf-8') as file:
                original_data = json.load(file)
            
            for segment in original_data['segments']:
                segment['text'] = substituir_texto(segment['text'], substituicoes_por_idioma['en'])
                for word in segment['words']:
                    word['word'] = substituir_texto(word['word'], substituicoes_por_idioma['en'])
            
            with open(original_file_path, 'w', encoding='utf-8') as file:
                json.dump(original_data, file, ensure_ascii=False, indent=2)

    print('Traduções e substituições concluídas.')

async def translate_project_subs(project_folder: str, target_lang: str):
    """
    Translates all _processed.json files in the 'subs' folder of the project.
    Creates a backup of the original as _original.json.
    """
    subs_folder = Path(project_folder) / "subs"
    if not subs_folder.exists():
        print(f"Subtitle folder not found: {subs_folder}")
        return

    # Look for files ending in _processed.json
    json_files = list(subs_folder.glob("*_processed.json"))
    
    if not json_files:
        print("No subtitle files found to translate.")
        return

    print(f"Found {len(json_files)} subtitle files to translate to '{target_lang}'...")

    for json_file in json_files:
        # Backup logic
        backup_file = json_file.with_name(json_file.stem + "_original" + json_file.suffix)
        
        source_file = json_file
        if backup_file.exists():
             print(f"Using existing backup for {json_file.name} as source.")
             source_file = backup_file
        else:
             print(f"Backing up original to {backup_file.name}...")
             try:
                # Rename current to backup
                json_file.rename(backup_file)
                source_file = backup_file
             except Exception as e:
                 print(f"Error creating backup for {json_file.name}: {e}")
                 continue
        
        # Translate source (backup) -> target (original filename)
        # effectively replacing the file read by the next step
        print(f"Translating {source_file.name} -> {json_file.name} ({target_lang})...")
        try:
            await translate_json_file(source_file, json_file, target_lang)
            
            # Apply language specific substitutions if any
            if target_lang in substituicoes_por_idioma:
                 with open(json_file, 'r', encoding='utf-8') as f:
                     data = json.load(f)
                 
                 modified = False
                 for segment in data.get('segments', []):
                    # Text
                    new_text = substituir_texto(segment['text'], substituicoes_por_idioma[target_lang])
                    if new_text != segment['text']:
                        segment['text'] = new_text
                        modified = True
                    
                    # Words
                    for word in segment.get('words', []):
                        w_text = word.get('word', '')
                        new_w_text = substituir_texto(w_text, substituicoes_por_idioma[target_lang])
                        if new_w_text != w_text:
                            word['word'] = new_w_text
                            modified = True
                 
                 if modified:
                     with open(json_file, 'w', encoding='utf-8') as f:
                         json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"Error translating {json_file.name}: {e}")
            # If failed and output doesn't exist, try to restore backup?
            if not json_file.exists() and backup_file.exists():
                print("Restoring backup due to failure...")
                backup_file.rename(json_file)

    print("Translation batch finished.")

if __name__ == "__main__":
    asyncio.run(main())