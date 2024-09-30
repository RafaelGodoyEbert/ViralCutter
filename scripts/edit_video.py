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
        
    def is_different_faces(landmarks1, landmarks2, threshold=0.3):
        # Calcular a distância entre os centros dos rostos
        center1 = np.mean([(landmark.x, landmark.y) for landmark in landmarks1], axis=0)
        center2 = np.mean([(landmark.x, landmark.y) for landmark in landmarks2], axis=0)
        distance = np.linalg.norm(center1 - center2)
        return distance > threshold
        
    import cv2
    import numpy as np

    def crop_and_resize_two_faces(frame, landmarks, zoom_factor):
        frame_height, frame_width = frame.shape[:2]

        if len(landmarks) < 2 or not is_different_faces(landmarks[0], landmarks[1]):
            return None

        # Definição dos limites dos rostos
        x_min1, x_max1, y_min1, y_max1 = (
            min(landmark.x for landmark in landmarks[0]),
            max(landmark.x for landmark in landmarks[0]),
            min(landmark.y for landmark in landmarks[0]),
            max(landmark.y for landmark in landmarks[0])
        )
        x_min2, x_max2, y_min2, y_max2 = (
            min(landmark.x for landmark in landmarks[1]),
            max(landmark.x for landmark in landmarks[1]),
            min(landmark.y for landmark in landmarks[1]),
            max(landmark.y for landmark in landmarks[1])
        )

        # Converter coordenadas para pixels
        face_coords = [
            (
                int(x_min * frame_width), int(x_max * frame_width),
                int(y_min * frame_height), int(y_max * frame_height)
            )
            for x_min, x_max, y_min, y_max in [(x_min1, x_max1, y_min1, y_max1), (x_min2, x_max2, y_min2, y_max2)]
        ]

        def calculate_crop_square(center_x, center_y, zoomed_width, zoomed_height):
            crop_size = max(zoomed_width, zoomed_height)
            crop_x_min = max(0, center_x - crop_size // 2)
            crop_y_min = max(0, center_y - crop_size // 2)
            crop_x_max = min(frame_width, crop_x_min + crop_size)
            crop_y_max = min(frame_height, crop_y_min + crop_size)
            return crop_x_min, crop_y_min, crop_x_max, crop_y_max

        faces_images = []
        
        for (face_x_min, face_x_max, face_y_min, face_y_max) in face_coords:
            # Calcular o centro e a largura/altura
            face_center_x = (face_x_min + face_x_max) // 2
            face_center_y = (face_y_min + face_y_max) // 2
            zoomed_width = int((face_x_max - face_x_min) * zoom_factor)
            zoomed_height = int((face_y_max - face_y_min) * zoom_factor)

            crop_coords = calculate_crop_square(face_center_x, face_center_y, zoomed_width, zoomed_height)
            face_image = frame[crop_coords[1]:crop_coords[3], crop_coords[0]:crop_coords[2]]
            
            # Resize e adicione à lista
            faces_images.append(cv2.resize(face_image, (1080, 960), interpolation=cv2.INTER_AREA))

        # Combinar rostos
        combined = np.vstack(faces_images)
        return combined

    # Exemplo de uso com captura de vídeo
    cap = cv2.VideoCapture("video_input.mp4")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Aqui você deve obter os landmarks
        landmarks = []  # Suponha que você tenha a lista de landmarks para os rostos

        combined_faces = crop_and_resize_two_faces(frame, landmarks, zoom_factor=1.5)
        if combined_faces is not None:
            cv2.imshow("Faces", combined_faces)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


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