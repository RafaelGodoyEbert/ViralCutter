import cv2
import mediapipe as mp
import numpy as np

def crop_and_resize_two_faces(frame, face_positions, zoom_out_factor=2.5):
    """
    Recorta e redimensiona dois rostos detectados no frame, ajustando para uma composição vertical
    1080x1920 onde cada rosto ocupa metade da tela, com um zoom mais afastado.
    """
    height, width, _ = frame.shape

    # Definir o tamanho da região de cada rosto
    crop_width = 1080
    crop_height = 960

    # Recortar e redimensionar o primeiro rosto
    x1, y1, w1, h1 = face_positions[0]

    # Ajustar o zoom aplicando um fator de afastamento
    x1_center = x1 + w1 // 2
    y1_center = y1 + h1 // 2
    new_w1 = int(w1 * zoom_out_factor)
    new_h1 = int(h1 * zoom_out_factor)

    x1_new = max(0, x1_center - new_w1 // 2)
    y1_new = max(0, y1_center - new_h1 // 2)

    face1 = frame[max(0, y1_new):min(height, y1_new + new_h1), max(0, x1_new):min(width, x1_new + new_w1)]
    face1_resized = cv2.resize(face1, (crop_width, crop_height))

    # Recortar e redimensionar o segundo rosto
    x2, y2, w2, h2 = face_positions[1]

    # Ajustar o zoom aplicando o fator de afastamento
    x2_center = x2 + w2 // 2
    y2_center = y2 + h2 // 2
    new_w2 = int(w2 * zoom_out_factor)
    new_h2 = int(h2 * zoom_out_factor)

    x2_new = max(0, x2_center - new_w2 // 2)
    y2_new = max(0, y2_center - new_h2 // 2)

    face2 = frame[max(0, y2_new):min(height, y2_new + new_h2), max(0, x2_new):min(width, x2_new + new_w2)]
    face2_resized = cv2.resize(face2, (crop_width, crop_height))

    # Criar uma tela de 1080x1920 para colocar os dois rostos
    result_frame = np.zeros((1920, 1080, 3), dtype=np.uint8)

    # Colocar os rostos na tela: primeiro em cima, segundo embaixo
    result_frame[0:960, :] = face1_resized
    result_frame[960:1920, :] = face2_resized

    return result_frame


def detect_face_or_body_two_faces(frame, face_detection, face_mesh, pose):
    # Converter a imagem para RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Processar a detecção de rosto
    results_face_detection = face_detection.process(frame_rgb)
    results_face_mesh = face_mesh.process(frame_rgb)
    results_pose = pose.process(frame_rgb)

    face_positions = []

    # Usar a detecção de rosto se disponível
    if results_face_detection.detections:
        for detection in results_face_detection.detections[:2]:  # Pegar até 2 rostos
            bbox = detection.location_data.relative_bounding_box
            x_min = int(bbox.xmin * frame.shape[1])
            y_min = int(bbox.ymin * frame.shape[0])
            width = int(bbox.width * frame.shape[1])
            height = int(bbox.height * frame.shape[0])
            face_positions.append((x_min, y_min, width, height))

        if len(face_positions) == 2:
            return face_positions

    # Usar landmarks do face mesh se disponível
    if results_face_mesh.multi_face_landmarks:
        for landmarks in results_face_mesh.multi_face_landmarks[:2]:  # Pegar até 2 rostos
            x_coords = [int(landmark.x * frame.shape[1]) for landmark in landmarks.landmark]
            y_coords = [int(landmark.y * frame.shape[0]) for landmark in landmarks.landmark]
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)
            width = x_max - x_min
            height = y_max - y_min
            face_positions.append((x_min, y_min, width, height))

        if len(face_positions) == 2:
            return face_positions

    # Se nenhum rosto for detectado, usar a pose para estimar o corpo
    if results_pose.pose_landmarks:
        x_coords = [lmk.x for lmk in results_pose.pose_landmarks.landmark]
        y_coords = [lmk.y for lmk in results_pose.pose_landmarks.landmark]
        x_min = int(min(x_coords) * frame.shape[1])
        x_max = int(max(x_coords) * frame.shape[1])
        y_min = int(min(y_coords) * frame.shape[0])
        y_max = int(max(y_coords) * frame.shape[0])
        width = x_max - x_min
        height = y_max - y_min
        return [(x_min, y_min, width, height)]

    return None

