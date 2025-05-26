import subprocess
import os
import sys
import torch
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def transcribe(input_file, model='medium'):
    print(f"Starting transcription of {input_file}...")
    start_time = time.time()  # Transcription start time
    
    output_folder = 'tmp'
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    srt_file = os.path.join(output_folder, f"{base_name}.srt")

    # Check if SRT file already exists
    if os.path.exists(srt_file):
        print(f"File {srt_file} already exists. Skipping transcription.")
        return srt_file

    # Force CPU for now due to WhisperX CUDA compatibility issues with RTX 5090
    device = "cpu"
    if torch.cuda.is_available():
        print(f"GPU detected ({torch.cuda.get_device_name(0)}), but using CPU mode for WhisperX compatibility.")
        print("Note: CUDA support for WhisperX with RTX 5090 is being investigated.")
    else:
        print("No GPU detected, using CPU.")

    # Use basic whisper as fallback due to WhisperX dependency conflicts
    command = [
        "whisper",
        input_file,
        "--model", model,
        "--task", "transcribe",
        "--verbose", "True",
        "--output_dir", output_folder,
        "--output_format", "srt",
        "--device", device
    ]

    try:
        print(f"Running transcription with model '{model}' on CPU...")
        print("This may take several minutes. Progress will be shown below:")
        print("Note: PyTorch Lightning version warnings can be safely ignored.")
        print("-" * 60)
        
        # Run with real-time output for progress tracking
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 universal_newlines=True, bufsize=1)
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())  # Show progress in real-time
        
        print("\nTranscription processing completed! Finalizing output files...")
        process.wait()  # Ensure process fully completes
        
        result_code = process.poll()
        if result_code != 0:
            raise subprocess.CalledProcessError(result_code, command)
            
        end_time = time.time()
        elapsed_time = end_time - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        print("-" * 60)
        print(f"Transcription completed. Output saved to {srt_file}.")
        print(f"Took {minutes} minutes and {seconds} seconds to transcribe using {device}.")
    except subprocess.CalledProcessError as e:
        print(f"Error during transcription: {e}")
        print("Transcription failed. Please check the video file and try again.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # Check if SRT file was created
    if os.path.exists(srt_file):
        print(f"SRT file {srt_file} created successfully.")
    else:
        print("Warning: SRT file was not created as expected.")

    return srt_file
