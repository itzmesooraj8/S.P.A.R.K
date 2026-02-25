import queue
import threading
from enum import Enum, auto

class SystemState(Enum):
    IDLE = auto()      # Waiting for wake word
    LISTENING = auto() # Recording user speech
    THINKING = auto()  # Processing text (LLM)
    SPEAKING = auto()  # TTS playback

class Pipeline:
    def __init__(self):
        self.state = SystemState.IDLE
        self.state_lock = threading.Lock()
        
        # Queues
        self.audio_queue = queue.Queue() # From Mic -> STT
        self.text_queue = queue.Queue()  # From STT -> LLM
        self.tools_queue = queue.Queue() # From LLM -> Tools
        self.speech_queue = queue.Queue() # From LLM -> TTS
        
        # Signals
        self.stop_signal = threading.Event() # SIG_STOP for barge-in

    def set_state(self, new_state):
        with self.state_lock:
            print(f"State Transition: {self.state} -> {new_state}")
            self.state = new_state

    def get_state(self):
        with self.state_lock:
            return self.state

    def trigger_barge_in(self):
        """
        Triggers the barge-in mechanism:
        1. Sets stop signal.
        2. Clears speech queue.
        3. Stops current TTS playback (handled by Output Thread).
        """
        print("!!! BARGE-IN DETECTED !!!")
        self.stop_signal.set()
        
        # Clear queues to stop pending actions
        with self.speech_queue.mutex:
            self.speech_queue.queue.clear()
        
        # Reset state to LISTENING immediately as we assume user wants to speak
        self.set_state(SystemState.LISTENING)

    def reset_barge_in(self):
        self.stop_signal.clear()
