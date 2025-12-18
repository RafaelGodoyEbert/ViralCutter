import cv2
import sys
import os

# Adjust path to import scripts
sys.path.append(os.getcwd())

try:
    from scripts.face_detection_insightface import init_insightface, suppress_stdout_stderr
    
    app = init_insightface()
    
    # Create a dummy frame (black) or try to read a real one if possible
    # We just want to check the attributes of the returned face object
    dummy = cv2.imread("C:/Users/rafam/.gemini/antigravity/brain/9bfedba9-72ff-4a40-a0d3-b77ea033233e/uploaded_image_1766002859958.png") # User uploaded image path from metadata?
    # Actually I don't have access to the user's uploaded image path on disk straightforwardly unless I guess, but I can use a black frame.
    # Wait, the user has processed videos in VIRALS folder.
    
    # Let's just use a black frame 640x640 containing a drawn white face square to trigger detection? Unlikely to work with InsightFace (needs features).
    # I will try to read one frame from a video in the workspace if exists.
    
    video_path = "c:\\Users\\rafam\\Downloads\\ViralCutter\\output000_original_scale.mp4" # Guessing from edit_video
    # Or search for mp4
    
    import glob
    videos = glob.glob("c:\\Users\\rafam\\Downloads\\ViralCutter\\**\\*.mp4", recursive=True)
    if videos:
        cap = cv2.VideoCapture(videos[0])
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            faces = app.get(frame)
            if faces:
                print("Face Keys:", faces[0].keys())
                if hasattr(faces[0], 'landmark_2d_106'):
                    print("Has 106 landmarks:", faces[0].landmark_2d_106 is not None)
                if hasattr(faces[0], 'landmark_3d_68'):
                    print("Has 68 landmarks:", faces[0].landmark_3d_68 is not None)
                print("Has kps:", faces[0].kps is not None)
            else:
                print("No faces found in sample frame.")
        else:
            print("Could not read frame.")
    else:
        print("No videos found to test.")

except Exception as e:
    print(f"Error: {e}")
