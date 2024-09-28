import cv2
import mediapipe as mp
import numpy as np
import os
import subprocess

def edit():
    # Inicializar Mediapipe FaceMesh
    mp_face_mesh = mp.solutions.face_mesh

    def crop_and_resize_single_face(frame, landmarks):
        frame_height, frame_width = frame.shape[:2]

        # Calcular o centro do rosto usando os landmarks
        x_min = min(landmark.x for landmark in landmarks)
        x_max = max(landmark.x for landmark in landmarks)
        y_min = min(landmark.y for landmark in landmarks)
        y_max = max(landmark.y for landmark in landmarks)

        face_center_x = int((x_min + x_max) * frame_width / 2)
        face_center_y = int((y_min + y_max) * frame_height / 2)

        # Calcular as coordenadas do crop
        target_height = int(frame_height * 0.8)  # Altura do rosto em 80% do vídeo
        target_width = int(target_height * (9 / 16))  # Largura proporcional a 9:16

        # Calcular as coordenadas do crop
        crop_x = max(0, face_center_x - target_width // 2)
        crop_y = max(0, face_center_y - target_height // 2)
        crop_x2 = min(crop_x + target_width, frame_width)
        crop_y2 = min(crop_y + target_height, frame_height)

        # Cortar a imagem e redimensionar para 9:16
        crop_img = frame[crop_y:crop_y2, crop_x:crop_x2]
        resized = cv2.resize(crop_img, (1080, 1920), interpolation=cv2.INTER_AREA)

        return resized

    def crop_and_resize_two_faces(frame, landmarks, zoom_factor):
        frame_height, frame_width = frame.shape[:2]

        # Calcular os limites do primeiro rosto
        x_min1 = min(landmark.x for landmark in landmarks[0])
        x_max1 = max(landmark.x for landmark in landmarks[0])
        y_min1 = min(landmark.y for landmark in landmarks[0])
        y_max1 = max(landmark.y for landmark in landmarks[0])

        # Calcular os limites do segundo rosto
        x_min2 = min(landmark.x for landmark in landmarks[1])
        x_max2 = max(landmark.x for landmark in landmarks[1])
        y_min2 = min(landmark.y for landmark in landmarks[1])
        y_max2 = max(landmark.y for landmark in landmarks[1])

        # Converter coordenadas para pixels
        face_x_min1, face_x_max1 = int(x_min1 * frame_width), int(x_max1 * frame_width)
        face_y_min1, face_y_max1 = int(y_min1 * frame_height), int(y_max1 * frame_height)

        face_x_min2, face_x_max2 = int(x_min2 * frame_width), int(x_max2 * frame_width)
        face_y_min2, face_y_max2 = int(y_min2 * frame_height), int(y_max2 * frame_height)

        # Calcular largura e altura dos rostos
        face_width1 = face_x_max1 - face_x_min1
        face_height1 = face_y_max1 - face_y_min1

        face_width2 = face_x_max2 - face_x_min2
        face_height2 = face_y_max2 - face_y_min2

        # Aplicar zoom para dar um pouco mais de espaço ao redor do rosto
        zoomed_width1 = int(face_width1 * zoom_factor)
        zoomed_height1 = int(face_height1 * zoom_factor)

        zoomed_width2 = int(face_width2 * zoom_factor)
        zoomed_height2 = int(face_height2 * zoom_factor)

        # Calcular o centro de cada rosto
        face_center_x1 = (face_x_min1 + face_x_max1) // 2
        face_center_y1 = (face_y_min1 + face_y_max1) // 2

        face_center_x2 = (face_x_min2 + face_x_max2) // 2
        face_center_y2 = (face_y_min2 + face_y_max2) // 2

        # Definir a área de corte (crop) mantendo a proporção quadrada para metade do vídeo (9:16)
        def calculate_crop_square(center_x, center_y, zoomed_width, zoomed_height):
            crop_size = max(zoomed_width, zoomed_height)  # Usar o maior entre largura e altura para manter o quadrado

            crop_x_min = max(0, center_x - crop_size // 2)
            crop_y_min = max(0, center_y - crop_size // 2)
            crop_x_max = min(frame_width, crop_x_min + crop_size)
            crop_y_max = min(frame_height, crop_y_min + crop_size)

            return crop_x_min, crop_y_min, crop_x_max, crop_y_max

        # Calcular as áreas de corte para cada rosto
        crop_x1_min, crop_y1_min, crop_x1_max, crop_y1_max = calculate_crop_square(
            face_center_x1, face_center_y1, zoomed_width1, zoomed_height1
        )
        crop_x2_min, crop_y2_min, crop_x2_max, crop_y2_max = calculate_crop_square(
            face_center_x2, face_center_y2, zoomed_width2, zoomed_height2
        )

        # Cortar a imagem para cada rosto
        face1_img = frame[crop_y1_min:crop_y1_max, crop_x1_min:crop_x1_max]
        face2_img = frame[crop_y2_min:crop_y2_max, crop_x2_min:crop_x2_max]

        # Garantir que os cortes para cada rosto sejam quadrados e manter a proporção
        face1_square = cv2.resize(face1_img, (1080, 960), interpolation=cv2.INTER_AREA)
        face2_square = cv2.resize(face2_img, (1080, 960), interpolation=cv2.INTER_AREA)

        # Combinar os dois rostos em uma única imagem (um em cima do outro, cada um com 960px de altura)
        combined = np.vstack((face1_square, face2_square))

        return combined

    def resize_with_padding(frame):
        frame_height, frame_width = frame.shape[:2]
        target_width, target_height = 1080, 1920  # 9:16 resolution

        # Calcular proporções
        target_ratio = target_width / target_height
        current_ratio = frame_width / frame_height

        if current_ratio > target_ratio:
            # O frame é mais largo que 9:16, ajustar largura
            new_width = target_width
            new_height = int(target_width / current_ratio)
        else:
            # O frame é mais alto que 9:16, ajustar altura
            new_height = target_height
            new_width = int(current_ratio * target_height)

        # Redimensionar o frame mantendo a proporção
        resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Calcular as bordas pretas
        top_padding = (target_height - new_height) // 2
        bottom_padding = target_height - new_height - top_padding
        left_padding = (target_width - new_width) // 2
        right_padding = target_width - new_width - left_padding

        # Adicionar as bordas pretas
        padded = cv2.copyMakeBorder(resized, top_padding, bottom_padding, left_padding, right_padding, cv2.BORDER_CONSTANT, value=[0, 0, 0])

        return padded

    def generate_short(input_file, output_file, original_file, index):
        try:
            face_mesh = mp_face_mesh.FaceMesh(max_num_faces=2, refine_landmarks=True, min_detection_confidence=0.5)
            cap = cv2.VideoCapture(input_file)

            if not cap.isOpened():
                print(f"Erro ao abrir o vídeo: {input_file}")
                return

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"Dimensões do vídeo - Altura: {frame_height}, Largura: {frame_width}, FPS: {fps}")

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_file, fourcc, fps, (1080, 1920))

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb_frame)

                if results.multi_face_landmarks and len(results.multi_face_landmarks) >= 2:
                    # Processar dois rostos com um fator de zoom
                    combined = crop_and_resize_two_faces(frame,
                                                        [results.multi_face_landmarks[0].landmark,
                                                          results.multi_face_landmarks[1].landmark],
                                                        zoom_factor=2.0)  # Ajuste esse valor conforme necessário
                    out.write(combined)
                elif results.multi_face_landmarks:
                    # Processar um rosto
                    landmarks = results.multi_face_landmarks[0].landmark
                    result = crop_and_resize_single_face(frame, landmarks)
                    out.write(result)
                else:
                    # Nenhum rosto detectado
                    result = resize_with_padding(frame)
                    out.write(result)

            cap.release()
            out.release()
            cv2.destroyAllWindows()
            face_mesh.close()

            audio_file = f"tmp/output-audio-{index}.aac"
            command = f"ffmpeg -y -i {input_file} -vn -acodec copy {audio_file}"

            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Erro ao extrair áudio: {result.stderr}")
                return

            if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
                final_dir = "final/"
                os.makedirs(final_dir, exist_ok=True)
                final_output = os.path.join(final_dir, f"final-output{str(index).zfill(3)}_processed.mp4")
                command = f"ffmpeg -y -i {output_file} -i {audio_file} -c:v h264_nvenc -preset fast -b:v 2M -c:a aac -b:a 192k -r {fps} {final_output}"
                subprocess.call(command, shell=True)
                print(f"Arquivo final gerado em: {final_output}")
            else:
                print(f"Erro ao extrair áudio do vídeo: {input_file}")

        except Exception as e:
            print(f"Erro durante o processamento do vídeo: {str(e)}")

    # Processamento de múltiplos vídeos
    index = 0
    while True:
        input_file = f'tmp/output{str(index).zfill(3)}_original_scale.mp4'
        output_file = f"tmp/output{str(index).zfill(3)}_processed.mp4"
        original_file = f'tmp/output{str(index).zfill(3)}.mp4'

        if os.path.exists(input_file):
            generate_short(input_file, output_file, original_file, index)
        else:
            print(f"Processamento completo até {index - 1} arquivos.")
            break

        index += 1
