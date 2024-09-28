import json
import re
import os

def adjust(base_color, base_size, h_size, highlight_color, palavras_por_bloco, limite_gap, modo, posicao_vertical, alinhamento):
    def gerar_ass(json_data, arquivo_saida, base_color=base_color, base_size=base_size, h_size=h_size, highlight_color=highlight_color, palavras_por_bloco=palavras_por_bloco, limite_gap=limite_gap, modo=modo, posicao_vertical=posicao_vertical, alinhamento=alinhamento):
        header_ass = f"""[Script Info]
    Title: Legendas Dinâmicas
    ScriptType: v4.00+
    PlayDepth: 0

    [V4+ Styles]
    Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    Style: Default,Arial,{base_size},&H00FFFFFF,{base_color},&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,1.5,0,{alinhamento},-2,-2,{posicao_vertical},1

    [Events]
    Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    """

        with open(arquivo_saida, "w", encoding="utf-8") as f:
            f.write(header_ass)

            for segment in json_data.get('segments', []):
                words = segment.get('words', [])
                total_words = len(words)

                i = 0
                while i < total_words:
                    block = []
                    while len(block) < palavras_por_bloco and i < total_words:
                        current_word = words[i]
                        if 'word' in current_word:
                            cleaned_word = re.sub(r'[.,!?;]', '', current_word['word'])
                            block.append({**current_word, 'word': cleaned_word})

                            if i + 1 < total_words:
                                next_word = words[i + 1]
                                if 'start' not in next_word or 'end' not in next_word:
                                    next_cleaned_word = re.sub(r'[.,!?;]', '', next_word['word'])
                                    block[-1]['word'] += " " + next_cleaned_word
                                    i += 1
                        i += 1

                    start_times = [word.get('start', 0) for word in block]
                    end_times = [word.get('end', 0) for word in block]

                    if modo == "highlight":
                        for j in range(len(block)):
                            line = ""
                            for k, word_data in enumerate(block):
                                word = word_data['word']
                                if k == j:
                                    line += f"{{\\fs{h_size}\\c{highlight_color}}}{word} "
                                else:
                                    line += f"{{\\fs{base_size}\\c&HFFFFFF&}}{word} "

                            start_time_ass = format_time_ass(start_times[j])
                            if j > 0 and (start_times[j] - end_times[j - 1] < limite_gap):
                                start_time_ass = format_time_ass(end_times[j - 1])

                            end_time_ass = format_time_ass(end_times[j])

                            f.write(f"Dialogue: 0,{start_time_ass},{end_time_ass},Default,,0,0,0,,{line.strip()}\n")

                    elif modo == "sem_higlight":
                        for j in range(len(block)):
                            line = " ".join(word_data['word'] for word_data in block)

                            start_time_ass = format_time_ass(start_times[j])
                            if j > 0 and (start_times[j] - end_times[j - 1] < limite_gap):
                                start_time_ass = format_time_ass(end_times[j - 1])

                            end_time_ass = format_time_ass(end_times[j])

                            f.write(f"Dialogue: 0,{start_time_ass},{end_time_ass},Default,,0,0,0,,{line.strip()}\n")

                    elif modo == "palavra_por_palavra":
                        for j in range(len(block)):
                            line = block[j]['word']
                            start_time_ass = format_time_ass(start_times[j])
                            end_time_ass = format_time_ass(end_times[j])
                            f.write(f"Dialogue: 0,{start_time_ass},{end_time_ass},Default,,0,0,0,,{line.strip()}\n")

    def format_time_ass(time_seconds):
        hours = int(time_seconds // 3600)
        minutes = int((time_seconds % 3600) // 60)
        seconds = int(time_seconds % 60)
        centiseconds = int((time_seconds % 1) * 100)
        return f"{hours:01}:{minutes:02}:{seconds:02}.{centiseconds:02}"

    # Diretórios de entrada e saída
    input_dir = "subs"
    output_dir = "subs_ass"

    # Criar o diretório de saída se não existir
    os.makedirs(output_dir, exist_ok=True)

    # Processar todos os arquivos JSON na pasta de entrada
    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            input_path = os.path.join(input_dir, filename)
            output_filename = os.path.splitext(filename)[0] + ".ass"
            output_path = os.path.join(output_dir, output_filename)

            # Carregar o arquivo JSON
            with open(input_path, "r", encoding="utf-8") as file:
                json_data = json.load(file)

            # Gerar o arquivo ASS
            gerar_ass(json_data, output_path, modo=modo, palavras_por_bloco=palavras_por_bloco, posicao_vertical=posicao_vertical, alinhamento=alinhamento)

            print(f"Arquivo processado: {filename} -> {output_filename}")

    print("Todos os arquivos JSON foram processados e convertidos para ASS.")