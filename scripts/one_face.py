import cv2
import numpy as np
import os
import subprocess
import mediapipe as mp

# Import quality enhancement functions
try:
    from scripts.video_quality import enhance_frame
    QUALITY_AVAILABLE = True
except ImportError:
    QUALITY_AVAILABLE = False

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
        # Use Lanczos for better upscaling quality
        resized = cv2.resize(crop_img, (1080, 1920), interpolation=cv2.INTER_LANCZOS4)
        
        # Apply full enhancement pipeline: Denoise -> Color Grading -> Unsharp
        if QUALITY_AVAILABLE:
            resized = enhance_frame(resized, preset_name="high")
        else:
            # Fallback to basic unsharp if module not available
            gaussian = cv2.GaussianBlur(resized, (0, 0), 3.0)
            resized = cv2.addWeighted(resized, 1.8, gaussian, -0.8, 0)

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
        return cv2.resize(result, (1080, 1920), interpolation=cv2.INTER_LANCZOS4)

def resize_with_blur_background(frame):
    """
    Composição de camadas: vídeo original nítido no centro + fundo desfocado (Blur Background).
    Preserva a qualidade nativa da imagem sem crop agressivo.
    Usa downscale antes do blur para economia de memória (~75% menos RAM).
    """
    frame_height, frame_width = frame.shape[:2]
    target_w, target_h = 1080, 1920
    target_ar = target_w / target_h  # 9/16 = 0.5625

    # === Background Layer (desfocado, preenche tudo) ===
    # Downscale para economia de memória antes do blur
    small_w, small_h = target_w // 2, target_h // 2  # 540x960

    # Fill-crop para o aspect ratio 9:16
    src_ar = frame_width / frame_height
    if src_ar > target_ar:
        # Mais largo que o target → crop lateral
        new_h = small_h
        new_w = int(small_h * src_ar)
    else:
        # Mais alto que o target → crop vertical
        new_w = small_w
        new_h = int(small_w / src_ar)

    bg_small = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Center crop to exact 540x960
    cx, cy = new_w // 2, new_h // 2
    x1 = max(0, cx - small_w // 2)
    y1 = max(0, cy - small_h // 2)
    bg_small = bg_small[y1:y1 + small_h, x1:x1 + small_w]

    # Gaussian Blur no frame pequeno (kernel grande para desfoque forte)
    bg_small = cv2.GaussianBlur(bg_small, (51, 51), 0)

    # Upscale para resolução final
    background = cv2.resize(bg_small, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

    # === Foreground Layer (nítido, aspect ratio original mantido) ===
    if src_ar > target_ar:
        # Fit by width
        fg_w = target_w
        fg_h = int(target_w / src_ar)
    else:
        # Fit by height
        fg_h = target_h
        fg_w = int(target_h * src_ar)

    foreground = cv2.resize(frame, (fg_w, fg_h), interpolation=cv2.INTER_LANCZOS4)

    # === Composição: foreground centralizado sobre background ===
    pad_top = (target_h - fg_h) // 2
    pad_left = (target_w - fg_w) // 2
    background[pad_top:pad_top + fg_h, pad_left:pad_left + fg_w] = foreground

    return background


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


def crop_center_zoom(frame):
    """
    Crops the center of the frame to fill 9:16 aspect ratio (Zoom effect).
    """
    frame_height, frame_width = frame.shape[:2]
    target_aspect_ratio = 9 / 16
    
    # Calculate crop dimensions to FILL the target ratio
    if frame_width / frame_height > target_aspect_ratio:
        # Source is wider than target (e.g. 16:9 source, 9:16 target) -> Crop Width
        new_width = int(frame_height * target_aspect_ratio)
        new_height = frame_height
    else:
        # Source is taller than target -> Crop Height
        new_width = frame_width
        new_height = int(frame_width / target_aspect_ratio)
        
    start_x = (frame_width - new_width) // 2
    start_y = (frame_height - new_height) // 2
    
    # Ensure bounds
    start_x = max(0, start_x)
    start_y = max(0, start_y)
    
    crop_img = frame[start_y:start_y+new_height, start_x:start_x+new_width]
    
    # Resize to final 1080x1920 with Lanczos for better quality
    resized = cv2.resize(crop_img, (1080, 1920), interpolation=cv2.INTER_LANCZOS4)
    
    # Apply full enhancement pipeline: Denoise -> Color Grading -> Unsharp
    if QUALITY_AVAILABLE:
        return enhance_frame(resized, preset_name="high")
    else:
        # Fallback to basic unsharp
        gaussian = cv2.GaussianBlur(resized, (0, 0), 3.0)
        return cv2.addWeighted(resized, 1.8, gaussian, -0.8, 0)

