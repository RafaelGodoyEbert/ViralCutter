import json
import os

def process_segments(data, start_time, end_time):
    new_segments = []
    
    for segment in data.get('segments', []):
        seg_start = segment.get('start', 0)
        seg_end = segment.get('end', 0)
        
        # Verifica interseção
        if seg_end <= start_time or seg_start >= end_time:
            continue
            
        # Calcula overlap
        # Ajusta timestamps relativos ao corte
        new_seg_start = max(0, seg_start - start_time)
        new_seg_end = min(end_time, seg_end) - start_time
        
        # Filtra palavras se existirem
        new_words = []
        if 'words' in segment:
            for word in segment['words']:
                w_start = word.get('start', 0)
                w_end = word.get('end', 0)
                
                if w_end > start_time and w_start < end_time:
                    new_w_start = max(0, w_start - start_time)
                    new_w_end = min(end_time, w_end) - start_time
                    word_copy = word.copy()
                    word_copy['start'] = new_w_start
                    word_copy['end'] = new_w_end
                    new_words.append(word_copy)
        
        # Se sobraram palavras ou se o segmento é válido no tempo
        if new_words or (new_seg_end > new_seg_start):
            new_segment = segment.copy()
            new_segment['start'] = new_seg_start
            new_segment['end'] = new_seg_end
            if 'words' in segment:
                new_segment['words'] = new_words
            new_segments.append(new_segment)
            
    return {'segments': new_segments}

def cut_json_transcript(input_json_path, output_json_path, start_time, end_time):
    """
    Lê o input.json (WhisperX), recorta o trecho e salva em output_json_path com timestamps ajustados.
    """
    if not os.path.exists(input_json_path):
        print(f"Aviso: {input_json_path} não encontrado. Não foi possível gerar JSON do corte.")
        return

    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        new_data = process_segments(data, start_time, end_time)
        
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
            
        print(f"JSON de legenda gerado: {output_json_path}")
        
    except Exception as e:
        print(f"Erro ao cortar JSON: {e}")
