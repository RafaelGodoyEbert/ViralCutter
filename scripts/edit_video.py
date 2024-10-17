import cv2
import numpy as np
import os
import subprocess
import mediapipe as mp
from scripts.one_face import crop_and_resize_single_face, resize_with_padding, detect_face_or_body
from scripts.two_face import crop_and_resize_two_faces, detect_face_or_body_two_faces

def edit():
    # Inicialização das soluções do MediaPipe
    mp_face_detection = mp.solutions.face_detection
    mp_face_mesh = mp.solutions.face_mesh
    mp_pose = mp.solutions.pose

    def generate_short(input_file, output_file, original_file, index, num_faces):
        try:
            cap = cv2.VideoCapture(input_file)

            if not cap.isOpened():
                print(f"Erro ao abrir o vídeo: {input_file}")
                return

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            print(f"Dimensões do vídeo - Altura: {frame_height}, Largura: {frame_width}, FPS: {fps}, Total de Frames: {total_frames}")

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_file, fourcc, fps, (1080, 1920))

            detection_interval = int(5 * fps)  # Verificar a cada 1 segundo
            last_detected_faces = None
            last_frame_face_positions = None
            frames_since_last_detection = 0
            max_frames_without_detection = detection_interval

            transition_duration = int(fps)  # Duração da transição suave (1 segundo)
            transition_frames = []

            # Inicializar as soluções do MediaPipe dentro de um contexto 'with' para garantir a liberação de recursos
            with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection, \
                 mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=2, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5) as face_mesh, \
                 mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:

                for frame_index in range(total_frames):
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break

                    # Detectar rostos ou corpos a cada 1 segundo
                    if frame_index % detection_interval == 0:
                        if num_faces == 2:
                            detections = detect_face_or_body_two_faces(frame, face_detection, face_mesh, pose)
                        else:  # num_faces == 1
                            detections = detect_face_or_body(frame, face_detection, face_mesh, pose)
                            if detections:
                                detections = [detections[0]]  # Garantir que temos apenas uma detecção

                        if detections and len(detections) == num_faces:
                            if last_frame_face_positions is not None:
                                # Iniciar transição suave
                                start_faces = np.array(last_frame_face_positions)
                                end_faces = np.array(detections)
                                transition_frames = np.linspace(start_faces, end_faces, transition_duration, dtype=int)
                            else:
                                transition_frames = []
                            last_detected_faces = detections
                            frames_since_last_detection = 0
                        else:
                            frames_since_last_detection += 1

                    # Aplicar transições suaves
                    if len(transition_frames) > 0:
                        current_faces = transition_frames[0]
                        transition_frames = transition_frames[1:]
                    elif last_detected_faces is not None and frames_since_last_detection <= max_frames_without_detection:
                        current_faces = last_detected_faces
                    else:
                        # Redimensionar o frame com padding se nenhum rosto for detectado
                        result = resize_with_padding(frame)
                        out.write(result)
                        continue

                    # Atualizar a última posição conhecida dos rostos
                    last_frame_face_positions = current_faces

                    # Aplicar o crop para dois rostos ou um rosto/corpo
                    if num_faces == 2:
                        result = crop_and_resize_two_faces(frame, current_faces)
                    else:
                        result = crop_and_resize_single_face(frame, current_faces[0])
                    out.write(result)

            cap.release()
            out.release()
            cv2.destroyAllWindows()

            # Extrair o áudio do vídeo original
            audio_file = f"tmp/output-audio-{index}.aac"
            command = f"ffmpeg -y -i {input_file} -vn -acodec copy {audio_file}"

            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Erro ao extrair o áudio: {result.stderr}")
                return

            if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
                final_dir = "final/"
                os.makedirs(final_dir, exist_ok=True)
                final_output = os.path.join(final_dir, f"final-output{str(index).zfill(3)}_processed.mp4")
                command = f"ffmpeg -y -i {output_file} -i {audio_file} -c:v h264_nvenc -preset fast -b:v 2M -c:a aac -b:a 192k -r {fps} {final_output}"
                subprocess.call(command, shell=True)
                print(f"Arquivo final gerado em: {final_output}")
            else:
                print(f"Erro ao extrair o áudio do vídeo: {input_file}")

        except Exception as e:
            print(f"Erro durante o processamento do vídeo: {str(e)}")


    # Processar múltiplos vídeos
    index = 0
    while True:
        input_file = f'tmp/output{str(index).zfill(3)}_original_scale.mp4'
        output_file = f"tmp/output{str(index).zfill(3)}_processed.mp4"
        original_file = f'tmp/output{str(index).zfill(3)}.mp4'

        if os.path.exists(input_file):
            # Definir o número de rostos esperados diretamente
            num_faces = 2  # ou 2, conforme sua necessidade
            # Verificar se o número de rostos é válido
            if num_faces in [1, 2]:
                generate_short(input_file, output_file, original_file, index, num_faces)
            else:
                print("Por favor, defina num_faces como 1 ou 2.")
        else:
            print(f"Processamento completo até {index - 1} arquivos.")
            break

        index += 1

if __name__ == "__main__":
    edit()