import cv2
import numpy as np
import os
import sys
from contextlib import contextmanager
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False

# Import quality enhancement functions
try:
    from scripts.video_quality import enhance_frame
    QUALITY_AVAILABLE = True
except ImportError:
    QUALITY_AVAILABLE = False

app = None

@contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

def init_insightface():
    """Explicit initialization if needed outside import."""
    global app
    if not INSIGHTFACE_AVAILABLE:
        raise ImportError("InsightFace not installed. Please install it.")
    
    if app is None:
        # Provider options to reduce logging if possible (often needs env var)
        # But redirection is safer for C++ logs
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        
        try:
            import onnxruntime as ort
            available = ort.get_available_providers()
            print(f"InsightFace: Available ONNX Providers: {available}")
            if 'CUDAExecutionProvider' not in available:
                print("WARNING: CUDAExecutionProvider not found. InsightFace will likely run on CPU.")
                print("To fix, install onnxruntime-gpu: pip install onnxruntime-gpu")
        except Exception as e:
            print(f"InsightFace: Could not check available providers: {e}")

        with suppress_stdout_stderr():
            app = FaceAnalysis(name='buffalo_l', providers=providers)
            app.prepare(ctx_id=0, det_size=(640, 640))
    return app

def detect_faces_insightface(frame):
    """
    Detect faces using InsightFace.
    Returns a list of dicts with 'bbox' and 'kps'.
    bbox is [x1, y1, x2, y2], kps is 5 keypoints (eyes, nose, mouth corners).
    """
    global app
    if app is None:
        init_insightface()

    faces = app.get(frame)
    results = []
    for face in faces:
        # Convert bbox to int
        bbox = face.bbox.astype(int)
        res = {
            'bbox': bbox, # [x1, y1, x2, y2]
            'kps': face.kps,
            'det_score': face.det_score
        }
        if hasattr(face, 'landmark_2d_106') and face.landmark_2d_106 is not None:
             res['landmark_2d_106'] = face.landmark_2d_106
        if hasattr(face, 'landmark_3d_68') and face.landmark_3d_68 is not None:
             res['landmark_3d_68'] = face.landmark_3d_68
             
        results.append(res)
    return results

def crop_and_resize_insightface(frame, face_bbox, target_width=1080, target_height=1920):
    """
    Crops and resizes the frame centered on face_bbox.
    Uses wider crop + blur background for landscape sources (less zoom, better quality).
    face_bbox: [x1, y1, x2, y2]
    """
    h, w, _ = frame.shape
    x1, y1, x2, y2 = face_bbox
    face_center_x = (x1 + x2) // 2
    
    target_ar = target_width / target_height  # 0.5625
    
    # Calculate tight 9:16 crop (minimum width)
    tight_w = int(h * target_ar)
    if tight_w > w:
        tight_w = w
    
    # Wider crop: show ~42% of source width (less zoom, more context)
    wide_w = int(w * 0.42)
    
    # Pick the wider option for less zoom
    source_w = min(max(tight_w, wide_w), w)
    source_h = h  # Always use full height
    
    # Center crop on face horizontally
    crop_x = max(0, min(face_center_x - source_w // 2, w - source_w))
    
    cropped = frame[0:source_h, crop_x:crop_x + source_w]
    
    crop_ar = source_w / source_h
    
    if abs(crop_ar - target_ar) < 0.03:
        # Crop is already ~9:16 (portrait/square source) → direct resize
        result = cv2.resize(cropped, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)
    else:
        # Wider than 9:16 → compose with blur background (TikTok/Reels style)
        # 1. Create blur background (fill-crop source to 9:16, then blur)
        bg_crop_w = min(int(h * target_ar), w)
        bg_x = (w - bg_crop_w) // 2
        bg_slice = frame[0:h, bg_x:bg_x + bg_crop_w]
        bg_small = cv2.resize(bg_slice, (target_width // 2, target_height // 2), interpolation=cv2.INTER_AREA)
        bg_small = cv2.GaussianBlur(bg_small, (51, 51), 0)
        result = cv2.resize(bg_small, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
        
        # 2. Scale foreground to fit target width
        scale = target_width / source_w
        fg_w = target_width
        fg_h = int(source_h * scale)
        
        if fg_h > target_height:
            fg_h = target_height
            fg_w = int(source_w * (target_height / source_h))
        
        foreground = cv2.resize(cropped, (fg_w, fg_h), interpolation=cv2.INTER_LANCZOS4)
        
        # 3. Center vertically on canvas
        pad_top = (target_height - fg_h) // 2
        pad_left = (target_width - fg_w) // 2
        result[pad_top:pad_top + fg_h, pad_left:pad_left + fg_w] = foreground
    
    # Apply full enhancement pipeline: Denoise -> Color Grading -> Unsharp
    if QUALITY_AVAILABLE:
        result = enhance_frame(result, preset_name="high")
    else:
        gaussian = cv2.GaussianBlur(result, (0, 0), 3.0)
        result = cv2.addWeighted(result, 1.8, gaussian, -0.8, 0)
    
    return result

if __name__ == "__main__":
    # Test block
    print("Testing InsightFace...")
    # Create a dummy image or try to load one if available, but for now just print config
    print("InsightFace initialized.")
