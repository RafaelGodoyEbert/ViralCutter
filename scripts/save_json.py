import os
import json

def save_viral_segments(segments_data=None):
    output_txt_file = "tmp/viral_segments.txt"

    # Verifica se o arquivo já existe
    if not os.path.exists(output_txt_file):
        if segments_data is None:
            # Solicita ao usuário que insira o JSON caso o arquivo não exista e os segmentos não estejam definidos
            user_input = input("Por favor, insira o JSON no formato desejado:\n")
            try:
                # Tenta carregar o JSON inserido
                segments_data = json.loads(user_input)

                # Valida se o formato está correto
                if "segments" in segments_data and isinstance(segments_data["segments"], list):
                    # Salva os dados em um arquivo JSON
                    with open(output_txt_file, 'w', encoding='utf-8') as file:
                        json.dump(segments_data, file, ensure_ascii=False, indent=4)
                    print(f"Segmentos virais salvos em {output_txt_file}")
                else:
                    print("Formato inválido. Certifique-se de que a estrutura está correta.")
            except json.JSONDecodeError:
                print("Erro ao decifrar o JSON. Por favor, verifique a formatação.")
        else:
            # Caso os segmentos tenham sido gerados, salva automaticamente
            with open(output_txt_file, 'w', encoding='utf-8') as file:
                json.dump(segments_data, file, ensure_ascii=False, indent=4)
            print(f"Segmentos virais salvos em {output_txt_file}")
    else:
        print(f"O arquivo {output_txt_file} já existe. Nenhuma entrada adicional é necessária.")
