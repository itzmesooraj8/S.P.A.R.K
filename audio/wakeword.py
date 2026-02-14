import openwakeword
from openwakeword.model import Model
import numpy as np
import onnxruntime 

class WakeWordDetector:
    def __init__(self):
        # Load the ONNX model
        self.model = Model(wakeword_models=["hey_jarvis_v0.1"], inference_framework="onnx")
        self.confidence_threshold = 0.5

    def process(self, audio_chunk):
        # Convert raw bytes to numpy int16
        audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
        
        # Get prediction
        prediction = self.model.predict(audio_int16)
        
        # Check if "hey_jarvis" score > threshold
        for model_name in prediction:
            if prediction[model_name] >= self.confidence_threshold:
                return True
        return False

    def delete(self):
        # Clean up resources (OpenWakeWord handles this mostly automatically, 
        # but we need this method to exist so main.py doesn't crash)
        pass
