import cv2
import time

class Camera:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index

    def capture_frame(self, save_path="vision_input.jpg"):
        """
        Captures a single frame from the webcam.
        Returns the absolute path to the saved image or None if failed.
        """
        import os
        save_path = os.path.abspath(save_path)
        print("Activating Camera...")
        cap = cv2.VideoCapture(self.camera_index)
        
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return None
            
        # Warmup
        for _ in range(5):
             cap.read()
             
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            cv2.imwrite(save_path, frame)
            print(f"Frame captured and saved to {save_path}")
            return save_path
        else:
            print("Error: Could not read frame.")
            return None
