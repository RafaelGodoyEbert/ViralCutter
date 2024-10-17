import cv2
import numpy as np
import os
import subprocess
import mediapipe as mp

def crop_and_resize_single_face(frame, face):
        frame_height, frame_width = frame.shape[:2]

        x, y, w, h = face
        face_center_x = x + w // 2
        face_center_y = y + h // 2

        # Cálculo da proporção desejada (9:16)
        target_aspect_ratio = 9 / 16

        # Cálculo da área de corte para evitar barras pretas
        if frame_width / frame_height > target_aspect_ratio:
            new_width = int(frame_height * target_aspect_ratio)
            new_height = frame_height
        else:
            new_width = frame_width
            new_height = int(frame_width / target_aspect_ratio)

        # Garantir que o corte esteja dentro dos limites
        crop_x = max(0, min(face_center_x - new_width // 2, frame_width - new_width))
        crop_y = max(0, min(face_center_y - new_height // 2, frame_height - new_height))
        crop_x2 = crop_x + new_width
        crop_y2 = crop_y + new_height

        # Recorte e redimensionamento para 1080x1920 (9:16)
        crop_img = frame[crop_y:crop_y2, crop_x:crop_x2]
        resized = cv2.resize(crop_img, (1080, 1920), interpolation=cv2.INTER_AREA)

        return resized

def resize_with_padding(frame):
        frame_height, frame_width = frame.shape[:2]
        target_aspect_ratio = 9 / 16

        if frame_width / frame_height > target_aspect_ratio:
            new_width = frame_width
            new_height = int(frame_width / target_aspect_ratio)
        else:
            new_height = frame_height
            new_width = int(frame_height * target_aspect_ratio)

        # Criação de uma tela preta
        result = np.zeros((new_height, new_width, 3), dtype=np.uint8)

        # Cálculo das margens
        pad_top = (new_height - frame_height) // 2
        pad_left = (new_width - frame_width) // 2

        # Colocar o frame original na tela
        result[pad_top:pad_top+frame_height, pad_left:pad_left+frame_width] = frame

        # Redimensionar para as dimensões finais
        return cv2.resize(result, (1080, 1920), interpolation=cv2.INTER_AREA)

def detect_face_or_body(frame, face_detection, face_mesh, pose):
    # Converter a imagem para RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Processar a detecção de rosto
    results_face_detection = face_detection.process(frame_rgb)
    results_face_mesh = face_mesh.process(frame_rgb)
    results_pose = pose.process(frame_rgb)

    detections = []

    # Usar a detecção de rosto se disponível
    if results_face_detection.detections:
        # Usar o primeiro rosto detectado
        detection = results_face_detection.detections[0]
        bbox = detection.location_data.relative_bounding_box
        x_min = int(bbox.xmin * frame.shape[1])
        y_min = int(bbox.ymin * frame.shape[0])
        width = int(bbox.width * frame.shape[1])
        height = int(bbox.height * frame.shape[0])
        detections.append((x_min, y_min, width, height))
    
    # Usar landmarks do face mesh se disponível
    if results_face_mesh.multi_face_landmarks:
        landmarks = results_face_mesh.multi_face_landmarks[0].landmark
        # Coordenadas do rosto baseadas nos pontos-chave (landmarks)
        x_coords = [int(landmark.x * frame.shape[1]) for landmark in landmarks]
        y_coords = [int(landmark.y * frame.shape[0]) for landmark in landmarks]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        width = x_max - x_min
        height = y_max - y_min
        detections.append((x_min, y_min, width, height))

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
        detections.append((x_min, y_min, width, height))

    # Se nada for detectado, retornar uma lista vazia
    return detections if detections else None

