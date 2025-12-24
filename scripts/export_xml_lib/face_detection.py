import os
try:
    import cv2
    import numpy as np
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    print("Warning: InsightFace not available. Dynamic cuts may fail if coords missing.")

def detect_faces_jit(video_path):
    """
    Runs face detection on the fly if pre-computed coords are missing.
    Returns: list of {'frame': int, 'faces': [[x1,y1,x2,y2]]}
    """
    if not INSIGHTFACE_AVAILABLE: 
        print("ERROR: InsightFace not loaded.")
        return []
    
    # Normalize path for Windows OpenCV
    video_path = os.path.abspath(video_path)
    print(f"Running JIT Face Detection on: {video_path}")
    
    # Initialize InsightFace
    try:
        app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))
    except Exception as e:
        print(f"InsightFace Init Error: {e}. Trying CPU only.")
        app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"CRITICAL ERROR: Could not open video file for JIT detection: {video_path}")
        # Try handling unicode path issues if any, though abspath helps
        return []

    face_data = []
    frame_idx = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video opened. Total frames: {total_frames}")
    
    faces_found_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        faces = app.get(frame)
        current_faces = []
        for face in faces:
            bbox = face.bbox.astype(int).tolist()
            current_faces.append(bbox)
        
        if current_faces:
            face_data.append({
                "frame": frame_idx,
                "faces": current_faces
            })
            faces_found_count += 1
            if faces_found_count <= 5: # Debug first few detections
                print(f"  [DEBUG] Frame {frame_idx}: Found {len(faces)} faces: {current_faces}")
            
        if frame_idx % 200 == 0:
            print(f"  Scanning faces: {frame_idx}/{total_frames}...")
            
        frame_idx += 1
        
    cap.release()
    print(f"JIT Detection Complete. Found faces in {len(face_data)} frames.")
    return face_data
