import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def transcribe():
    def generate_whisperx(input_file, output_folder, model='large-v3'):
        output_file = os.path.join(output_folder, f"{os.path.splitext(os.path.basename(input_file))[0]}.srt")
        json_file = os.path.join(output_folder, f"{os.path.splitext(os.path.basename(input_file))[0]}.json")  # Define the JSON output file

        # Skip processing if the JSON file already exists
        if os.path.exists(json_file):
            print(f"Arquivo já existe, pulando: {json_file}")
            return

        command = [
            "whisperx",
            input_file,
            "--model", model,
            "--task", "transcribe",
            "--align_model", "WAV2VEC2_ASR_LARGE_LV60K_960H",
            "--chunk_size", "10",
            "--vad_onset", "0.4",
            "--vad_offset", "0.3",
            "--compute_type", "float32",
            "--batch_size", "10",
            "--output_dir", output_folder,
            "--output_format", "srt",
            "--output_format", "json",
        ]

        print(f"Transcrevendo: {input_file}...")
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        print(f"Comando executado: {command}")
        
        if result.returncode != 0:
            print("Erro durante a transcrição:")
            print(result.stderr)
        else:
            print(f"Transcrição concluída. Arquivo salvo em: {output_file} e {json_file}")
            print(result.stdout)  # Verificar a saída correta

    # Define o diretório de entrada e o diretório de saída
    input_folder = 'final/'
    output_folder = 'subs/'

    # Itera sobre todos os arquivos na pasta de entrada
    for filename in os.listdir(input_folder):
        if filename.endswith('.mp4'):  # Filtra apenas arquivos .mp4
            input_file = os.path.join(input_folder, filename)
            generate_whisperx(input_file, output_folder)

