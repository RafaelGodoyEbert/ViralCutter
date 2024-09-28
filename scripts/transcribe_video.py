import subprocess
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def srt_to_tsv(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f_in, open(output_file, 'w', encoding='utf-8') as f_out:
        subtitle_lines = f_in.read().strip().split('\n\n')

        for subtitle_block in subtitle_lines:
            subtitle = subtitle_block.strip().split('\n')
            if len(subtitle) < 3:  # Ignora blocos incompletos
                continue

            subtitle_number = subtitle[0]
            time_range = subtitle[1]
            subtitle_text = ' '.join(subtitle[2:])

            f_out.write(f"{subtitle_number}\t{time_range}\t{subtitle_text}\n")
            
def transcribe(input_file, model='large-v3'):
    output_folder = 'tmp'
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    srt_file = os.path.join(output_folder, f"{base_name}.srt")
    tsv_file = os.path.join(output_folder, f"{base_name}.tsv")

    # Verifica se os arquivos de saída já existem
    if os.path.exists(srt_file) and os.path.exists(tsv_file):
        print(f"Os arquivos {srt_file} e {tsv_file} já existem. Pulando a transcrição.")
        return srt_file, tsv_file

    command = [
        "whisperx",
        input_file,
        "--model", model,
        "--task", "transcribe",
        "--align_model", "WAV2VEC2_ASR_LARGE_LV60K_960H",
        "--interpolate_method", "linear",
        "--chunk_size", "10",
        "--verbose", "True",
        "--vad_onset", "0.4",
        "--vad_offset", "0.3",
        "--no_align",
        "--segment_resolution", "sentence",
        "--compute_type", "float32",
        "--batch_size", "10",
        "--output_dir", output_folder,
        "--output_format", "srt",
        "--print_progress", "True"
    ]

    try:
        print(f"Starting transcription of {input_file}...")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Transcription completed. Output saved to {srt_file}.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error during transcription: {e}")
        print(f"Error output: {e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # Verifica se o arquivo SRT foi criado e converte para TSV
    if os.path.exists(srt_file):
        print("Converting SRT to TSV...")
        srt_to_tsv(srt_file, tsv_file)
        print(f"Conversion completed. TSV saved to {tsv_file}.")
    else:
        print("Warning: SRT file was not created as expected.")

    return srt_file, tsv_file


