import cv2
import mediapipe as mp
import numpy as np

def crop_and_maintain_ar(frame, face_box, target_w, target_h, zoom_out_factor=2.2):
    """
    Recorta uma região baseada no rosto mantendo o aspect ratio do target.
    Previne deformação (esticar/espremer).
    """
    img_h, img_w, _ = frame.shape
    x, y, w, h = face_box
    
    # Centro do rosto
    cx = x + w // 2
    cy = y + h // 2
    
    # Dimensão base do rosto (maior lado para garantir cobertura)
    face_size = max(w, h)
    
    # Altura desejada do crop (altura do rosto * fator de zoom/afastamento)
    # zoom_out_factor: quanto maior, mais afastado (mais cenário)
    req_h = face_size * zoom_out_factor
    
    # Aspect Ratio alvo (1080 / 960 = 1.125)
    target_ar = target_w / target_h
    
    # Calcular largura e altura do crop mantendo AR
    crop_h = req_h
    crop_w = crop_h * target_ar
    
    # Verificar limitações da imagem original (não podemos cortar mais que existe)
    # Se a largura necessária for maior que a imagem, limitamos pela largura
    if crop_w > img_w:
        crop_w = float(img_w)
        crop_h = crop_w / target_ar
        
    # Se a altura necessária for maior que a imagem, limitamos pela altura
    if crop_h > img_h:
        crop_h = float(img_h)
        crop_w = crop_h * target_ar
        
    # Converter para inteiros
    crop_w = int(crop_w)
    crop_h = int(crop_h)
    
    # Calcular coordenadas top-left do crop centralizado no rosto
    x1 = int(cx - crop_w // 2)
    y1 = int(cy - crop_h // 2)
    
    # Ajuste de bordas (Clamp) deslisando a janela se possível
    # Se sair pela esquerda, encosta na esquerda
    if x1 < 0: 
        x1 = 0
    # Se sair pela direita, encosta na direita
    elif x1 + crop_w > img_w: 
        x1 = img_w - crop_w
        
    # Se sair por cima
    if y1 < 0: 
        y1 = 0
    # Se sair por baixo
    elif y1 + crop_h > img_h: 
        y1 = img_h - crop_h
    
    # Verificação de segurança final se a imagem for menor que o crop (embora lógica acima evite)
    x2 = x1 + crop_w
    y2 = y1 + crop_h
    
    # Crop
    cropped = frame[y1:y2, x1:x2]
    
    # Se o crop falhar (tamanho 0), retorna preto
    if cropped.size == 0 or cropped.shape[0] == 0 or cropped.shape[1] == 0:
        return np.zeros((target_h, target_w, 3), dtype=np.uint8)

    # Redimensionar para o tamanho alvo final (1080x960)
    # Como garantimos o AR, o resize mantém a proporção correta
    resized = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
    return resized

def crop_and_resize_two_faces(frame, face_positions, zoom_out_factor=2.2):
    """
    Recorta e redimensiona dois rostos detectados no frame, ajustando para uma composição vertical
    1080x1920 onde cada rosto ocupa metade da tela (1080x960).
    """
    # Target dimensoes para cada metade
    target_w = 1080
    target_h = 960
    
    # Se não temos 2 faces, fallback (segurança)
    if len(face_positions) < 2:
        return np.zeros((1920, 1080, 3), dtype=np.uint8)

    # Primeiro rosto (Topo)
    face1_img = crop_and_maintain_ar(frame, face_positions[0], target_w, target_h, zoom_out_factor)
    
    # Segundo rosto (Embaixo)
    face2_img = crop_and_maintain_ar(frame, face_positions[1], target_w, target_h, zoom_out_factor)
    
    # Compor imagem final (Stack Vertical)
    result_frame = np.vstack((face1_img, face2_img))
    
    return result_frame


def detect_face_or_body_two_faces(frame, face_detection, face_mesh, pose):
    # Converter a imagem para RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Processar a detecção de rosto
    results_face_detection = face_detection.process(frame_rgb)
    results_face_mesh = face_mesh.process(frame_rgb)
    results_pose = pose.process(frame_rgb)

    face_positions_detection = []
    if results_face_detection.detections:
        for detection in results_face_detection.detections[:2]:
            bbox = detection.location_data.relative_bounding_box
            x_min = int(bbox.xmin * frame.shape[1])
            y_min = int(bbox.ymin * frame.shape[0])
            width = int(bbox.width * frame.shape[1])
            height = int(bbox.height * frame.shape[0])
            face_positions_detection.append((x_min, y_min, width, height))

    if len(face_positions_detection) == 2:
        return face_positions_detection

    face_positions_mesh = []
    if results_face_mesh.multi_face_landmarks:
        for landmarks in results_face_mesh.multi_face_landmarks[:2]:
            x_coords = [int(landmark.x * frame.shape[1]) for landmark in landmarks.landmark]
            y_coords = [int(landmark.y * frame.shape[0]) for landmark in landmarks.landmark]
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)
            width = x_max - x_min
            height = y_max - y_min
            face_positions_mesh.append((x_min, y_min, width, height))

    if len(face_positions_mesh) == 2:
        return face_positions_mesh
        
    # If neither found 2, return what we found (prefer detection as it is bounding box optimized)
    if face_positions_detection:
        return face_positions_detection
    if face_positions_mesh:
        return face_positions_mesh

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
