import cv2
import numpy as np
import os
import subprocess
import mediapipe as mp
from scripts.one_face import crop_and_resize_single_face, resize_with_padding, detect_face_or_body
from scripts.two_face import crop_and_resize_two_faces, detect_face_or_body_two_faces

def edit():
    # Initialize MediaPipe solutions
    mp_face_detection = mp.solutions.face_detection
    mp_face_mesh = mp.solutions.face_mesh
    mp_pose = mp.solutions.pose

    def generate_short(input_file, output_file, original_file, index, num_faces):
        try:
            cap = cv2.VideoCapture(input_file)

            if not cap.isOpened():
                print(f"Error opening video: {input_file}")
                return

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            print(f"Video dimensions - Height: {frame_height}, Width: {frame_width}, FPS: {fps}, Total Frames: {total_frames}")

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_file, fourcc, fps, (1080, 1920))

            detection_interval = int(5 * fps)  # Check every 1 second
            last_detected_faces = None
            last_frame_face_positions = None
            frames_since_last_detection = 0
            max_frames_without_detection = detection_interval

            transition_duration = int(fps)  # Smooth transition duration (1 second)
            transition_frames = []

            # Initialize MediaPipe solutions within a 'with' context to ensure resource cleanup
            with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection, \
                 mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=2, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5) as face_mesh, \
                 mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:

                for frame_index in range(total_frames):
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break

                    # Detect faces or bodies every 1 second
                    if frame_index % detection_interval == 0:
                        if num_faces == 2:
                            detections = detect_face_or_body_two_faces(frame, face_detection, face_mesh, pose)
                        else:  # num_faces == 1
                            detections = detect_face_or_body(frame, face_detection, face_mesh, pose)
                            if detections:
                                detections = [detections[0]]  # Ensure we have only one detection

                        if detections and len(detections) == num_faces:
                            if last_frame_face_positions is not None:
                                # Start smooth transition
                                start_faces = np.array(last_frame_face_positions)
                                end_faces = np.array(detections)
                                transition_frames = np.linspace(start_faces, end_faces, transition_duration, dtype=int)
                            else:
                                transition_frames = []
                            last_detected_faces = detections
                            frames_since_last_detection = 0
                        else:
                            frames_since_last_detection += 1

                    # Apply smooth transitions
                    if len(transition_frames) > 0:
                        current_faces = transition_frames[0]
                        transition_frames = transition_frames[1:]
                    elif last_detected_faces is not None and frames_since_last_detection <= max_frames_without_detection:
                        current_faces = last_detected_faces
                    else:
                        # Resize frame with padding if no face is detected
                        result = resize_with_padding(frame)
                        out.write(result)
                        continue

                    # Update the last known position of faces
                    last_frame_face_positions = current_faces

                    # Apply crop for two faces or one face/body
                    if num_faces == 2:
                        result = crop_and_resize_two_faces(frame, current_faces)
                    else:
                        result = crop_and_resize_single_face(frame, current_faces[0])
                    out.write(result)

            cap.release()
            out.release()
            cv2.destroyAllWindows()

            # Extract audio from original video
            audio_file = f"tmp/output-audio-{index}.aac"
            command = f"ffmpeg -y -i {input_file} -vn -acodec copy {audio_file}"

            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error extracting audio: {result.stderr}")
                return

            if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
                final_dir = "final/"
                os.makedirs(final_dir, exist_ok=True)
                final_output = os.path.join(final_dir, f"final-output{str(index).zfill(3)}_processed.mp4")
                command = f"ffmpeg -y -i {output_file} -i {audio_file} -c:v h264_nvenc -preset fast -b:v 2M -c:a aac -b:a 192k -r {fps} {final_output}"
                subprocess.call(command, shell=True)
                print(f"Final file generated at: {final_output}")
            else:
                print(f"Error extracting audio from video: {input_file}")

        except Exception as e:
            print(f"Error during video processing: {str(e)}")


    # Process multiple videos
    index = 0
    while True:
        input_file = f'tmp/output{str(index).zfill(3)}_original_scale.mp4'
        output_file = f"tmp/output{str(index).zfill(3)}_processed.mp4"
        original_file = f'tmp/output{str(index).zfill(3)}.mp4'

        if os.path.exists(input_file):
            # Define the expected number of faces directly
            num_faces = 2  # or 2, according to your needs
            # Check if the number of faces is valid
            if num_faces in [1, 2]:
                generate_short(input_file, output_file, original_file, index, num_faces)
            else:
                print("Please define num_faces as 1 or 2.")
        else:
            print(f"Processing complete up to {index - 1} files.")
            break

        index += 1

if __name__ == "__main__":
    edit()