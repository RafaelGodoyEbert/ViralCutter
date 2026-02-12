# Face Tracking with Ultralytics YOLO and Smooth Zoom
"""
This module provides YOLO-based face detection and tracking with EMA smoothing
for a "cinematic" camera follow effect.

Features:
- Uses YOLOv8 tracking with ByteTrack for persistent face IDs
- EMA smoothing for smooth camera movement
- Automatic GPU detection (CUDA)
- Fallback to InsightFace or center crop if YOLO fails
"""

import cv2
import numpy as np
import os
import subprocess

# Lazy import to avoid errors if ultralytics is not installed
YOLO_AVAILABLE = False
YOLO_MODEL = None

def init_yolo(model_name="yolov8n.pt"):
    """
    Initialize YOLO model for tracking.
    Tries yolov8n-face.pt first, then falls back to yolov8n.pt
    """
    global YOLO_AVAILABLE, YOLO_MODEL
    
    try:
        from ultralytics import YOLO
        import torch
        
        # Determine device
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"[YOLO] Using device: {device}")
        
        # Try to find face-specific model first
        models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        face_model_path = os.path.join(models_dir, "yolov8n-face.pt")
        
        if os.path.exists(face_model_path):
            print(f"[YOLO] Loading face model: {face_model_path}")
            YOLO_MODEL = YOLO(face_model_path)
        else:
            print(f"[YOLO] Face model not found. Using default: {model_name}")
            YOLO_MODEL = YOLO(model_name)
        
        YOLO_MODEL.to(device)
        YOLO_AVAILABLE = True
        print("[YOLO] Initialization successful!")
        return True
        
    except ImportError as e:
        print(f"[YOLO] ultralytics not installed: {e}")
        YOLO_AVAILABLE = False
        return False
    except Exception as e:
        print(f"[YOLO] Initialization failed: {e}")
        YOLO_AVAILABLE = False
        return False


class SmoothBBox:
    """
    Exponential Moving Average (EMA) smoothing for bounding boxes.
    Provides smooth face tracking without zoom effects.
    """
    
    def __init__(self, alpha=0.05):
        """
        Args:
            alpha: Smoothing factor (0.0 = no movement, 1.0 = instant snap)
                   0.05 = smooth but responsive tracking
        """
        self.alpha = alpha
        self.smooth_bbox = None
        self.target_bbox = None
        self.frames_without_detection = 0
        self.max_frames_hold = 90
    
    def update(self, detected_bbox):
        """
        Update the smooth bounding box with a new detection.
        
        Args:
            detected_bbox: (x1, y1, x2, y2) or None if no detection
            
        Returns:
            Tuple of (smoothed_bbox, zoom) - zoom is always 1.0 (no zoom)
        """
        if detected_bbox is not None:
            self.target_bbox = np.array(detected_bbox, dtype=float)
            self.frames_without_detection = 0
            
            if self.smooth_bbox is None:
                # First detection - snap to it
                self.smooth_bbox = self.target_bbox.copy()
            else:
                # Apply EMA smoothing
                self.smooth_bbox = (
                    self.alpha * self.target_bbox + 
                    (1 - self.alpha) * self.smooth_bbox
                )
        else:
            # No detection - hold position
            self.frames_without_detection += 1
            
            if self.frames_without_detection > self.max_frames_hold:
                return None, 1.0
        
        if self.smooth_bbox is not None:
            return tuple(self.smooth_bbox.astype(int)), 1.0
        return None, 1.0
    
    def reset(self):
        """Reset the smoother state."""
        self.smooth_bbox = None
        self.target_bbox = None
        self.frames_without_detection = 0


def get_best_encoder():
    """Detect best available video encoder."""
    try:
        result = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], 
                              capture_output=True, text=True)
        output = result.stdout
        
        if "h264_nvenc" in output:
            return ("h264_nvenc", "fast")
        if "h264_amf" in output:
            return ("h264_amf", "speed")
        if "h264_qsv" in output:
            return ("h264_qsv", "veryfast")
        if "h264_videotoolbox" in output:
            return ("h264_videotoolbox", "default")
    except Exception:
        pass
    
    return ("libx264", "ultrafast")


def crop_to_vertical(frame, center_x, center_y, frame_width, frame_height, zoom=1.0):
    """
    Crop frame to 9:16 aspect ratio centered on (center_x, center_y) with progressive zoom.
    
    Args:
        frame: Input frame
        center_x, center_y: Center point to focus on
        frame_width, frame_height: Original frame dimensions
        zoom: Zoom factor (1.0 = no zoom, 1.4 = 40% closer)
    """
    target_aspect = 9 / 16
    
    # Calculate base crop dimensions
    if frame_width / frame_height > target_aspect:
        base_crop_width = int(frame_height * target_aspect)
        base_crop_height = frame_height
    else:
        base_crop_width = frame_width
        base_crop_height = int(frame_width / target_aspect)
    
    # Apply zoom - smaller crop = more zoomed in
    crop_width = int(base_crop_width / zoom)
    crop_height = int(base_crop_height / zoom)
    
    # Ensure minimum crop size (avoid too much zoom)
    min_crop_width = int(base_crop_width / 2.0)  # Max 2x zoom
    min_crop_height = int(base_crop_height / 2.0)
    crop_width = max(crop_width, min_crop_width)
    crop_height = max(crop_height, min_crop_height)
    
    # Calculate crop position (centered on face)
    crop_x = int(center_x - crop_width // 2)
    crop_y = int(center_y - crop_height // 2)
    
    # Clamp to frame bounds
    crop_x = max(0, min(crop_x, frame_width - crop_width))
    crop_y = max(0, min(crop_y, frame_height - crop_height))
    
    # Extract and resize
    crop = frame[crop_y:crop_y+crop_height, crop_x:crop_x+crop_width]
    return cv2.resize(crop, (1080, 1920), interpolation=cv2.INTER_AREA)


def generate_short_yolo(input_file, output_file, index, project_folder, final_folder,
                        face_mode="auto", no_face_mode="zoom", alpha=0.05):
    """
    Process video with YOLO tracking and smooth face following.
    
    Args:
        input_file: Path to input video
        output_file: Path for temporary output
        index: Segment index
        project_folder: Project folder path
        final_folder: Final output folder
        face_mode: "auto", "1", or "2"
        no_face_mode: "zoom" or "padding" when no face detected
        alpha: EMA smoothing factor (0.02=Ultra Smooth, 0.05=Normal, 0.10=Fast)
    """
    global YOLO_MODEL
    
    if not YOLO_AVAILABLE or YOLO_MODEL is None:
        raise RuntimeError("YOLO not initialized. Call init_yolo() first.")
    
    print(f"[YOLO] Processing with smooth tracking (alpha={alpha}): {input_file}")
    
    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {input_file}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Initialize smoother with alpha from UI
    smoother = SmoothBBox(alpha=alpha)
    
    # Video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, fps, (1080, 1920))
    
    # Track the dominant person (by ID persistence or size)
    tracked_id = None
    
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Run YOLO tracking
        # persist=True maintains tracking IDs across frames
        results = YOLO_MODEL.track(frame, persist=True, conf=0.3, iou=0.5, 
                                   verbose=False, classes=[0])  # class 0 = person
        
        # Extract best detection
        best_bbox = None
        
        if results and len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            
            if len(boxes) > 0:
                # Get boxes data
                xyxy = boxes.xyxy.cpu().numpy()  # (x1, y1, x2, y2)
                confs = boxes.conf.cpu().numpy()
                ids = boxes.id.cpu().numpy() if boxes.id is not None else None
                
                # Strategy: Track the same person if possible, else pick largest
                if tracked_id is not None and ids is not None:
                    # Try to find our tracked person
                    match_idx = np.where(ids == tracked_id)[0]
                    if len(match_idx) > 0:
                        best_bbox = xyxy[match_idx[0]]
                
                if best_bbox is None:
                    # Pick largest (by area)
                    areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
                    best_idx = np.argmax(areas)
                    best_bbox = xyxy[best_idx]
                    
                    # Remember this person's ID for tracking
                    if ids is not None:
                        tracked_id = ids[best_idx]
        
        # Apply EMA smoothing with progressive zoom
        smoothed, current_zoom = smoother.update(best_bbox)
        
        if smoothed is not None:
            # Calculate face center
            x1, y1, x2, y2 = smoothed
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            # Crop and resize with progressive zoom
            result = crop_to_vertical(frame, center_x, center_y, 
                                     frame_width, frame_height, zoom=current_zoom)
        else:
            # Fallback: center crop or padding (still use progressive zoom)
            if no_face_mode == "zoom":
                # Center crop with current zoom level
                result = crop_to_vertical(frame, frame_width/2, frame_height/2,
                                         frame_width, frame_height, zoom=current_zoom)
            else:
                # Padding (import from one_face)
                from scripts.one_face import resize_with_padding
                result = resize_with_padding(frame)
        
        out.write(result)
        frame_idx += 1
        
        # Progress indicator every 100 frames
        if frame_idx % 100 == 0:
            print(f"[YOLO] Progress: {frame_idx}/{total_frames} frames")
    
    cap.release()
    out.release()
    
    print(f"[YOLO] Processing complete: {frame_idx} frames")
    
    # Finalize (mux audio)
    _finalize_video(input_file, output_file, index, fps, project_folder, final_folder)
    
    return "1"  # Return face mode for compatibility


def _finalize_video(input_file, output_file, index, fps, project_folder, final_folder):
    """Mux audio with processed video."""
    audio_file = os.path.join(project_folder, "cuts", f"output-audio-{index}.aac")
    
    # Extract audio
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", input_file, "-vn", "-acodec", "copy", audio_file
    ], check=False, capture_output=True)
    
    if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
        final_output = os.path.join(final_folder, f"final-output{str(index).zfill(3)}_processed.mp4")
        encoder_name, encoder_preset = get_best_encoder()
        
        command = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats",
            "-i", output_file,
            "-i", audio_file,
            "-c:v", encoder_name, "-preset", encoder_preset, "-b:v", "5M",
            "-c:a", "aac", "-b:a", "192k",
            "-r", str(fps),
            final_output
        ]
        
        try:
            subprocess.run(command, check=True)
            print(f"[YOLO] Final output: {final_output}")
            
            # Cleanup temp files
            try:
                os.remove(audio_file)
                os.remove(output_file)
            except:
                pass
                
        except subprocess.CalledProcessError as e:
            print(f"[YOLO] Muxing error: {e}")
    else:
        print(f"[YOLO] Warning: No audio extracted for {input_file}")


# Convenience function to check if YOLO is ready
def is_yolo_available():
    return YOLO_AVAILABLE and YOLO_MODEL is not None
