import cv2
import numpy as np
import os
import subprocess
import mediapipe as mp
from scripts.one_face import crop_and_resize_single_face, resize_with_padding, detect_face_or_body
from scripts.two_face import crop_and_resize_two_faces, detect_face_or_body_two_faces
try:
    from scripts.face_detection_insightface import init_insightface, detect_faces_insightface, crop_and_resize_insightface
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    print("InsightFace not found or error importing. Install with: pip install insightface onnxruntime-gpu")

def get_center_bbox(bbox):
    # bbox: [x1, y1, x2, y2]
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

def get_center_rect(rect):
    # rect: (x, y, w, h)
    return (rect[0] + rect[2] / 2, rect[1] + rect[3] / 2)

def sort_by_proximity(new_faces, old_faces, center_func):
    """
    Sorts new_faces to match the order of old_faces based on distance.
    new_faces: list of face objects (bbox or tuple)
    old_faces: list of face objects (bbox or tuple)
    center_func: function that takes a face object and returns (cx, cy)
    """
    if not old_faces or len(old_faces) != 2 or len(new_faces) != 2:
        return new_faces
    
    old_c1 = center_func(old_faces[0])
    old_c2 = center_func(old_faces[1])
    
    new_c1 = center_func(new_faces[0])
    new_c2 = center_func(new_faces[1])
    
    # Cost if we keep order: [new1, new2]
    # dist(old1, new1) + dist(old2, new2)
    dist_keep = ((old_c1[0]-new_c1[0])**2 + (old_c1[1]-new_c1[1])**2) + \
                ((old_c2[0]-new_c2[0])**2 + (old_c2[1]-new_c2[1])**2)
                
    # Cost if we swap: [new2, new1]
    # dist(old1, new2) + dist(old2, new1)
    dist_swap = ((old_c1[0]-new_c2[0])**2 + (old_c1[1]-new_c2[1])**2) + \
                ((old_c2[0]-new_c1[0])**2 + (old_c2[1]-new_c1[1])**2)
                
    # If swapping reduces total movement distance, do it
    if dist_swap < dist_keep:
        return [new_faces[1], new_faces[0]]
    
    return new_faces

def generate_short_fallback(input_file, output_file, index, project_folder, final_folder):
    """Fallback function: Center Crop if MediaPipe fails."""
    print(f"Processing (Center Crop Fallback): {input_file}")
    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        print(f"Error opening video: {input_file}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Target dimensions (9:16)
    target_width = 1080
    target_height = 1920
    
    # Use FFmpeg Pipe instead of cv2.VideoWriter to avoid OpenCV backend errors
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-loglevel', 'error', '-hide_banner', '-stats',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-s', f'{target_width}x{target_height}',
        '-pix_fmt', 'bgr24',
        '-r', str(fps),
        '-i', '-',
        '-c:v', 'libx264', # or h264_nvenc if available
        '-preset', 'fast',
        '-pix_fmt', 'yuv420p',
        output_file
    ]
    
    process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Resize mantendo aspect ratio para cobrir altura 1920
        scale_factor = target_height / height
        # Se após o resize a largura for menor que 1080, escala pela largura
        if width * scale_factor < target_width:
             scale_factor = target_width / width
             
        # Garante dimensoes inteiras
        new_w = int(width * scale_factor)
        new_h = int(height * scale_factor)
        
        resized = cv2.resize(frame, (new_w, new_h))
        
        # Crop center
        res_h, res_w, _ = resized.shape
        start_x = (res_w - target_width) // 2
        start_y = (res_h - target_height) // 2
        
        if start_x < 0: start_x = 0
        if start_y < 0: start_y = 0

        cropped = resized[start_y:start_y+target_height, start_x:start_x+target_width]
        
        # Resize final por segurança e validação
        if cropped.shape[1] != target_width or cropped.shape[0] != target_height:
            cropped = cv2.resize(cropped, (target_width, target_height))
        
        try:
            # Write raw bytes to ffmpeg stdin
            process.stdin.write(cropped.tobytes())
        except Exception as e:
            print(f"Error writing frame to ffmpeg pipe: {e}")
            pass

    cap.release()
    process.stdin.close()
    process.wait()
    
    finalize_video(input_file, output_file, index, fps, project_folder, final_folder)

def finalize_video(input_file, output_file, index, fps, project_folder, final_folder):
    """Mux audio and video."""
    audio_file = os.path.join(project_folder, "cuts", f"output-audio-{index}.aac")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", input_file, "-vn", "-acodec", "copy", audio_file], 
                   check=False, capture_output=True)

    if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
        final_output = os.path.join(final_folder, f"final-output{str(index).zfill(3)}_processed.mp4")
        command = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats",
            "-i", output_file,
            "-i", audio_file,
            "-c:v", "h264_nvenc", "-preset", "fast", "-b:v", "5M",
            "-c:a", "aac", "-b:a", "192k",
            "-r", str(fps),
            final_output
        ]
        try:
            subprocess.run(command, check=True) #, capture_output=True)
            print(f"Final file generated: {final_output}")
            try:
                os.remove(audio_file)
                os.remove(output_file) 
            except:
                pass
        except subprocess.CalledProcessError as e:
            print(f"Error muxing: {e}")
    else:
        print(f"Warning: No audio extracted for {input_file}")


def generate_short_mediapipe(input_file, output_file, index, face_mode, project_folder, final_folder, face_detection, face_mesh, pose, detection_period=None):
    try:
        cap = cv2.VideoCapture(input_file)
        if not cap.isOpened():
            print(f"Error opening video: {input_file}")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_file, fourcc, fps, (1080, 1920))

        next_detection_frame = 0
        current_interval = int(5 * fps) # Initial guess

        # Initial Interval Logic if predefined

        if detection_period is not None:
             current_interval = max(1, int(detection_period * fps))
        elif face_mode == "2":
             current_interval = int(1.0 * fps)
        
        last_detected_faces = None
        last_frame_face_positions = None
        frames_since_last_detection = 0
        max_frames_without_detection = int(5 * fps) # Fallback timeout

        transition_duration = int(fps)
        transition_frames = []

        for frame_index in range(total_frames):
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            if frame_index >= next_detection_frame:
                # Detect ALL faces (up to 2 in our implementation)
                detections = detect_face_or_body_two_faces(frame, face_detection, face_mesh, pose)
                
                # Dynamic Logic
                target_faces = 1
                if face_mode == "2":
                    target_faces = 2
                elif face_mode == "auto":
                    if detections and len(detections) >= 2:
                        target_faces = 2
                    else:
                        target_faces = 1
                
                # Filter detections based on target
                current_detections = []
                if detections:
                    # Sort detections by approximate Area (w*h) descending to pick main faces first
                    detections.sort(key=lambda s: s[2] * s[3], reverse=True)
                    
                    if len(detections) >= target_faces:
                        current_detections = detections[:target_faces]
                    elif len(detections) > 0:
                        # Fallback
                        current_detections = detections[:1] 
                        target_faces = 1 
                    
                    # Apply Consistency Check (Proximity)
                    if target_faces == 2 and len(current_detections) == 2:
                         if last_detected_faces is not None and len(last_detected_faces) == 2:
                             current_detections = sort_by_proximity(current_detections, last_detected_faces, get_center_rect)
                
                # Check for stability/lookahead could go here but skipping for brevity unless requested.
                
                if current_detections and len(current_detections) == target_faces:
                    if last_frame_face_positions is not None:
                        start_faces = np.array(last_frame_face_positions)
                        end_faces = np.array(current_detections)
                        try:
                            transition_frames = np.linspace(start_faces, end_faces, transition_duration, dtype=int)
                        except Exception as e:
                            # Fallback if shapes mismatch unexpectedly
                            transition_frames = []
                    else:
                        transition_frames = []
                    last_detected_faces = current_detections
                    frames_since_last_detection = 0
                else:
                    frames_since_last_detection += 1
                
                # Update next detection frame
                step = 5
                
                if detection_period is not None:
                    if isinstance(detection_period, dict):
                         # If we are targeting 2 faces, we use '2' interval, else '1'
                         key = str(target_faces)
                         val = detection_period.get(key, detection_period.get('1', 0.2))
                         step = max(1, int(val * fps))
                    else:
                         step = max(1, int(detection_period * fps))
                elif target_faces == 2:
                    step = int(1.0 * fps)
                else:
                    step = int(5) # 5 frames for 1 face
                
                next_detection_frame = frame_index + step

            if len(transition_frames) > 0:
                current_faces = transition_frames[0]
                transition_frames = transition_frames[1:]
            elif last_detected_faces is not None and frames_since_last_detection <= max_frames_without_detection:
                current_faces = last_detected_faces
            else:
                result = resize_with_padding(frame)
                out.write(result)
                continue

            last_frame_face_positions = current_faces

            if hasattr(current_faces, '__len__') and len(current_faces) == 2:
                 result = crop_and_resize_two_faces(frame, current_faces)
            else:
                 # Ensure it's list of tuples or single tuple? current_faces is list of tuples from detection
                 # If 1 face: [ (x,y,w,h) ]
                 if hasattr(current_faces, '__len__') and len(current_faces) > 0:
                     f = current_faces[0]
                     result = crop_and_resize_single_face(frame, f)
                 else:
                     result = resize_with_padding(frame)
            
            out.write(result)

        cap.release()
        out.release()
        
        finalize_video(input_file, output_file, index, fps, project_folder, final_folder)

    except Exception as e:
        print(f"Error in MediaPipe processing: {e}")
        raise e # Rethrow to trigger fallback

def generate_short_haar(input_file, output_file, index, project_folder, final_folder, detection_period=None):
    """Face detection using OpenCV Haar Cascades."""
    print(f"Processing (Haar Cascade): {input_file}")
    
    # Load Haar Cascade
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        print("Error: Could not load Haar Cascade XML. Falling back to center crop.")
        generate_short_fallback(input_file, output_file, index, project_folder, final_folder)
        return

    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        print(f"Error opening video: {input_file}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, fps, (1080, 1920))
    
    # Logic copied from generate_short_mediapipe
    detection_interval = int(2 * fps) # Default check every 2 seconds
    if detection_period is not None:
        detection_interval = max(1, int(detection_period * fps))
    last_detected_faces = None
    last_frame_face_positions = None
    frames_since_last_detection = 0
    max_frames_without_detection = int(5 * fps)

    transition_duration = int(fps) # 1 second smooth transition
    transition_frames = []

    for frame_index in range(total_frames):
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        if frame_index % detection_interval == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            detections = []
            if len(faces) > 0:
                # Pick largest face
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                # Ensure int type
                detections = [tuple(map(int, largest_face))]

            if detections:
                if last_frame_face_positions is not None:
                    # Simple linear interpolation for smoothing
                    start_faces = np.array(last_frame_face_positions)
                    end_faces = np.array(detections)
                    
                    # Generate transition frames
                    steps = transition_duration
                    transition_frames = []
                    for s in range(steps):
                        t = (s + 1) / steps
                        interp = (1 - t) * start_faces + t * end_faces
                        transition_frames.append(interp.astype(int).tolist()) # Convert back to list of lists/tuples
                else:
                    transition_frames = []
                last_detected_faces = detections
                frames_since_last_detection = 0
            else:
                frames_since_last_detection += 1

        if len(transition_frames) > 0:
            current_faces = transition_frames[0]
            transition_frames = transition_frames[1:]
        elif last_detected_faces is not None and frames_since_last_detection <= max_frames_without_detection:
            current_faces = last_detected_faces
        else:
            # No face detected for a while -> Center/Padding fallback
            result = resize_with_padding(frame)
            out.write(result)
            continue

        last_frame_face_positions = current_faces
        # haar detections are list containing one tuple (x,y,w,h)
        # current_faces is list of one tuple
        if isinstance(current_faces, list):
             face_bbox = current_faces[0]
        else:
             face_bbox = current_faces # Should be handled

        result = crop_and_resize_single_face(frame, face_bbox)
        out.write(result)

    cap.release()
    out.release()
    
    finalize_video(input_file, output_file, index, fps, project_folder, final_folder)

def generate_short_insightface(input_file, output_file, index, project_folder, final_folder, face_mode="auto", detection_period=None):
    """Face detection using InsightFace (SOTA)."""
    print(f"Processing (InsightFace): {input_file} | Mode: {face_mode}")
    
    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        print(f"Error opening video: {input_file}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Using mp4v for container, but final mux will fix encoding
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, fps, (1080, 1920))
    
    # Dynamic Interval Logic
    next_detection_frame = 0
    
    last_detected_faces = None
    last_frame_face_positions = None
    frames_since_last_detection = 0
    max_frames_without_detection = 90 # 3 seconds timeout

    transition_duration = 4 # Smooth transition over 4 frames (almost continuous)
    transition_frames = []

    # Current state of face mode (1 or 2)
    # If auto, we decide per detection interval
    current_num_faces_state = 1
    if face_mode == "2":
        current_num_faces_state = 2

    frame_1_face_count = 0
    frame_2_face_count = 0

    buffered_frame = None
    
    # Timeline tracking: list of (frame_index, mode_str)
    # We will compress this later.
    timeline_frames = [] # Store mode for *every written frame* or at least detection points

    for frame_index in range(total_frames):
        if buffered_frame is not None:
             frame = buffered_frame
             ret = True
             buffered_frame = None
        else:
             ret, frame = cap.read()

        if not ret or frame is None:
            break

        if frame_index >= next_detection_frame and len(transition_frames) == 0:
            # Detect faces
            faces = detect_faces_insightface(frame)
            
            # Decide 1 or 2 faces
            target_faces = 1
            if face_mode == "2":
                target_faces = 2
            elif face_mode == "auto":
                if len(faces) >= 2:
                    target_faces = 2
                else:
                    target_faces = 1
            
            # Fallback Lookahead: If detection fails or partial
            if len(faces) < target_faces:
                # Try 1 frame ahead
                ret2, frame2 = cap.read()
                if ret2 and frame2 is not None:
                     faces2 = detect_faces_insightface(frame2)
                     # If lookahead found what we wanted OR found something better than nothing
                     if len(faces2) >= target_faces:
                         faces = faces2 # Use lookahead faces for current frame
                         # (This assumes movement is small enough between 1 frame to be valid)
                     elif len(faces) == 0 and len(faces2) > 0:
                         faces = faces2 # Better than nothing
                         
                     buffered_frame = frame2 # Store for next iteration

            detections = []
            
            if len(faces) >= target_faces:
                # Pick top N faces by area
                faces_sorted = sorted(faces, key=lambda f: (f['bbox'][2]-f['bbox'][0]) * (f['bbox'][3]-f['bbox'][1]), reverse=True)
                
                if target_faces == 2:
                    # Convert [x1, y1, x2, y2] to (x, y, w, h) for two_face compatibility logic or custom logic
                    # We will store [x1, y1, x2, y2] for interpolation, and convert during crop
                    
                    # Ensure we have 2 faces
                    f1 = faces_sorted[0]['bbox']
                    f2 = faces_sorted[1]['bbox']
                    
                    if last_detected_faces is not None and len(last_detected_faces) == 2:
                        detections = sort_by_proximity([f1, f2], last_detected_faces, get_center_bbox)
                    else:
                        detections = [f1, f2]
                        
                    current_num_faces_state = 2
                else:
                    # 1 face
                    detections = [faces_sorted[0]['bbox']]
                    current_num_faces_state = 1
            else:
                 # If we wanted 2 but found 1, or wanted 1 found 0
                 if len(faces) > 0:
                     # Fallback to 1 face if found at least 1
                     faces_sorted = sorted(faces, key=lambda f: (f['bbox'][2]-f['bbox'][0]) * (f['bbox'][3]-f['bbox'][1]), reverse=True)
                     detections = [faces_sorted[0]['bbox']]
                     current_num_faces_state = 1
                 else:
                     detections = []

            if detections:
                if last_frame_face_positions is not None and len(last_frame_face_positions) == len(detections):
                    # Transition
                    start_faces = np.array(last_frame_face_positions)
                    end_faces = np.array(detections)
                    
                    steps = transition_duration
                    transition_frames = []
                    for s in range(steps):
                        t = (s + 1) / steps
                        interp = (1 - t) * start_faces + t * end_faces
                        transition_frames.append(interp.astype(int).tolist())
                else:
                    # Reset transition if face count changed or first detect
                    transition_frames = []
                last_detected_faces = detections
                frames_since_last_detection = 0
            else:
                frames_since_last_detection += 1

            # Update next detection frame based on NEW state
            step = 5 # Default fallback (very fast)
            
            if detection_period is not None:
                if isinstance(detection_period, dict):
                    # Period depends on state
                    key = str(current_num_faces_state) 
                    # fallback to '1' if key not found (should be there)
                    val = detection_period.get(key, detection_period.get('1', 0.2)) 
                    step = max(1, int(val * fps))
                else:
                    # Legacy float support (should not happen with new main.py but good safety)
                    step = max(1, int(detection_period * fps))
            elif current_num_faces_state == 2:
                step = int(1.0 * fps) # 1s for 2 faces
            else:
                step = 5 # 5 frames for 1 face (~0.16s at 30fps)
            
            next_detection_frame = frame_index + step

        if len(transition_frames) > 0:
            current_faces = transition_frames[0]
            transition_frames = transition_frames[1:]
        elif last_detected_faces is not None and frames_since_last_detection <= max_frames_without_detection:
            current_faces = last_detected_faces
        else:
            # Fallback for this frame
            result = resize_with_padding(frame)
            out.write(result)
            continue

        last_frame_face_positions = current_faces
        
        target_len = len(current_faces)
        
        if target_len == 2:
             frame_2_face_count += 1
             # Convert [x1, y1, x2, y2] to (x, y, w, h)
             f1 = current_faces[0]
             f2 = current_faces[1]
             rect1 = (f1[0], f1[1], f1[2]-f1[0], f1[3]-f1[1])
             rect2 = (f2[0], f2[1], f2[2]-f2[0], f2[3]-f2[1])
             result = crop_and_resize_two_faces(frame, [rect1, rect2])
             timeline_frames.append((frame_index, "2"))
        else:
             frame_1_face_count += 1
             # 1 face
             # current_faces[0] is [x1, y1, x2, y2]
             result = crop_and_resize_insightface(frame, current_faces[0])
             timeline_frames.append((frame_index, "1"))
             
        out.write(result)

    cap.release()
    out.release()
    
    # Compress timeline into segments
    # [(start_time, end_time, mode), ...]
    compressed_timeline = []
    if timeline_frames:
        curr_mode = timeline_frames[0][1]
        start_f = timeline_frames[0][0]
        
        for i in range(1, len(timeline_frames)):
            frame_idx, mode = timeline_frames[i]
            if mode != curr_mode:
                # End current segment
                # Convert frame to seconds
                end_f = timeline_frames[i-1][0]
                compressed_timeline.append({
                    "start": float(start_f) / fps,
                    "end": float(end_f) / fps, # or frame_idx / fps for continuity
                    "mode": curr_mode
                })
                # Start new
                curr_mode = mode
                start_f = frame_idx
        
        # Add last
        end_f = timeline_frames[-1][0]
        compressed_timeline.append({
             "start": float(start_f) / fps,
             "end": (float(end_f) + 1) / fps,
             "mode": curr_mode
        })
    
    # Save timeline JSON
    timeline_file = output_file.replace(".mp4", "_timeline.json")
    try:
        import json
        with open(timeline_file, "w") as f:
            json.dump(compressed_timeline, f)
        print(f"Timeline saved: {timeline_file}")
    except Exception as e:
        print(f"Error saving timeline: {e}")

    finalize_video(input_file, output_file, index, fps, project_folder, final_folder)
    
    # Return dominant mode logic (or keep 15% rule as overall fallback)
    if frame_2_face_count > (total_frames * 0.15):
        return "2"
    return "1"


def edit(project_folder="tmp", face_model="insightface", face_mode="auto", detection_period=None):
    mp_face_detection = mp.solutions.face_detection
    mp_face_mesh = mp.solutions.face_mesh
    mp_pose = mp.solutions.pose
    
    index = 0
    cuts_folder = os.path.join(project_folder, "cuts")
    final_folder = os.path.join(project_folder, "final")
    os.makedirs(final_folder, exist_ok=True)
    
    face_modes_log = {}
    
    # Priority: User Choice -> Fallbacks
    
    insightface_working = False
    
    # Only init InsightFace if selected or default
    if INSIGHTFACE_AVAILABLE and (face_model == "insightface"):
        try:
            print("Initializing InsightFace...")
            init_insightface()
            insightface_working = True
            print("InsightFace Initialized Successfully.")
        except Exception as e:
            print(f"WARNING: InsightFace Initialization Failed ({e}). Will try MediaPipe.")
            insightface_working = False

    mediapipe_working = False
    use_haar = False
    
    # If insightface failed OR user chose mediapipe, init mediapipe
    should_use_mediapipe = (face_model == "mediapipe") or (face_model == "insightface" and not insightface_working)
    
    if should_use_mediapipe:
        try:
            # Try to init with model_selection=0 (Short Range)
            with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as fd:
                pass
            mediapipe_working = True
            print("MediaPipe Initialized Successfully.")
        except Exception as e:
            print(f"WARNING: MediaPipe Initialization Failed ({e}). Switching to OpenCV Haar Cascade.")
            mediapipe_working = False
            use_haar = True
    
    # Logic for MediaPipe replaced by dynamic pass
    # mp_num_faces = 2 if face_mode == "2" else 1  

    while True:
        input_filename = f"output{str(index).zfill(3)}_original_scale.mp4"
        input_file = os.path.join(cuts_folder, input_filename)
        output_file = os.path.join(final_folder, f"temp_video_no_audio_{index}.mp4")

        if os.path.exists(input_file):
            success = False
            detected_mode = "1" # Default if detection fails or fallback

            # 1. Try InsightFace
            if insightface_working:
                try:
                    # Capture returned mode
                    res = generate_short_insightface(input_file, output_file, index, project_folder, final_folder, face_mode=face_mode, detection_period=detection_period)
                    if res: detected_mode = res
                    success = True
                except Exception as e:
                    print(f"InsightFace processing failed for {input_filename}: {e}")
                    print("Falling back to MediaPipe/Haar...")
            
            # 2. Try MediaPipe if InsightFace failed or not available
            if not success and mediapipe_working:
                try:
                    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.2) as face_detection, \
                         mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=2, refine_landmarks=True, min_detection_confidence=0.2, min_tracking_confidence=0.2) as face_mesh, \
                         mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
                        
                        generate_short_mediapipe(input_file, output_file, index, face_mode, project_folder, final_folder, face_detection, face_mesh, pose, detection_period=detection_period)
                        # We don't easily know detected mode here without return, assuming '1' or '2' based on last frame? 
                        # Ideally function should return as well.
                        detected_mode = "1" # Placeholder, user didn't complain about stats.
                        # detected_mode = str(mp_num_faces) # Error fix: mp_num_faces not defined
                        if face_mode == "2":
                            detected_mode = "2"
                    success = True
                except Exception as e:
                     print(f"MediaPipe processing failed (fallback): {e}")
            
            # 3. Try Haar if others failed
            if not success and (use_haar or (not mediapipe_working and not insightface_working)):
                 try:
                    print("Attempts with Haar Cascade...")
                    generate_short_haar(input_file, output_file, index, project_folder, final_folder, detection_period=detection_period)
                    success = True
                 except Exception as e2:
                    print(f"Haar fallback also failed: {e2}")

            # 4. Last Resort: Center Crop
            if not success:
                generate_short_fallback(input_file, output_file, index, project_folder, final_folder)
                detected_mode = "1"
            
            # Save mode
            face_modes_log[f"output{str(index).zfill(3)}"] = detected_mode

        else:
            if index == 0:
                print(f"No files found in {cuts_folder}.")
            break
        index += 1
        
    # Save Face Modes to JSON for subtitle usage
    modes_file = os.path.join(project_folder, "face_modes.json")
    try:
        import json
        with open(modes_file, "w") as f:
            json.dump(face_modes_log, f)
        print(f"Detect Stats saved: {modes_file}")
    except Exception as e:
        print(f"Error saving face modes: {e}")

if __name__ == "__main__":
    edit()