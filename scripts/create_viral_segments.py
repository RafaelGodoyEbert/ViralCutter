import json

def create(num_segments, viral_mode, themes, tempo_minimo, tempo_maximo):
    quantidade_de_virals = num_segments  # @param {type:"number"}

    with open('tmp/input_video.tsv', 'r', encoding='utf-8') as f:
        content = f.read()

    system = f"You are a Viral Segment Identifier, an AI system that analyzes a video's transcript and predicts which segments might go viral on social media platforms. You use factors such as emotional impact, humor, unexpected content, and relevance to current trends to make your predictions. You return a structured text document detailing the start and end times, the description, the duration, and a viral score for the potential viral segments."

    json_template = '''
            { "segments" :
                [
                    {
                        "title": "Suggested Viral Title",
                        "start_time": "00:00:00", #HH:MM:SS
                        "end_time": "00:00:00", #HH:MM:SS
                        "description": "Description of the text",
                        "duration": 0,
                        "score": 0  # Probability of going viral (0-100)
                    }
                ]
            }
        '''

    # Split content into chunks of 14,000 characters without cutting lines
    chunk_size = 17400
    chunks = []
    start = 0

    while start < len(content):
        end = min(start + chunk_size, len(content))
        if end < len(content):
            end = content.rfind('\n', start, end)  # Find last newline before chunk size
            if end == -1:  # No newline found, just take the chunk size
                end = start + chunk_size
        chunks.append(content[start:end])
        start = end

    # Prepare the output texts
    #@markdown <h1>Se viral está marcado, os temas não serão executados.</h1>
    viral = None #@param{type:"boolean"}
    #@markdown <h1>Se viral está desmarcado, a IA vai procurar os temas selecionadas</h1>

    #@markdown Exemplo: ``GTA VI, cadeirada datena, as luas de júpiter``
    temas = '' # @param {type:"string", placeholder:"Coloque o tema aqui, se mais que um, separado por virgulas"}

    if viral_mode:
        type = f"""analyze the segment for potential virality and identify {quantidade_de_virals} most viral segments from the transcript"""
    else:
        type = f"""analyze the segment for potential virality and identify {quantidade_de_virals} the best parts based on the list of themes {themes}."""

    output_texts = []
    for i, chunk in enumerate(chunks):
        if len(chunks) == 1:
            output_text = f"""
    {system}\n
    Given the following video transcript, {type}. Each segment must have a duration between {tempo_minimo} and {tempo_maximo} seconds. It is MANDATORY to respect the specified number of viral segments, the minimum duration, and the maximum duration. Additionally, the cuts MUST MAKE SENSE and cannot end abruptly without context. The provided transcript is as follows:
    {chunk}
    Based on your analysis, return a structured text document containing the timestamps (start and end), the description of the viral part, its duration, a suggested viral title, and a score indicating the probability of going viral. Please follow this format for each segment.
    {json_template}
    The total duration must be within a minimum time of {tempo_minimo} seconds and a maximum time of {tempo_maximo} seconds.
    """
        else:
            if i == 0:
                output_text = f"""
    {chunk}
    """
            elif i < len(chunks) - 1:
                output_text = f"""
    Vou enviar outra parte da legenda, analise e responda com OK, assim envio mais partes da legenda.

    {chunk}
    """
            else:
                output_text = f"""
    Vou enviar outra parte da legenda, analise e responda com OK, assim envio mais partes da legenda.

    {chunk}\n\n
    {system}\n
    Given the following video transcript, {type}. Each segment must have a duration between {tempo_minimo} and {tempo_maximo} seconds. It is MANDATORY to respect the specified number of viral segments, the minimum duration, and the maximum duration. Additionally, the cuts MUST MAKE SENSE and cannot end abruptly without context. The provided transcript is as follows:
    {chunk}
    Based on your analysis, return a structured text document containing the timestamps (start and end), the description of the viral part, its duration, a suggested viral title, and a score indicating the probability of going viral. Please follow this format for each segment. Leave the 'title' and 'description' in the language the subtitles are in.
    {json_template}
    The total duration must be within a minimum time of {tempo_minimo} seconds and a maximum time of {tempo_maximo} seconds.
    """

        output_texts.append(output_text)

    # Print the output texts
    for text in output_texts:
        print(text)