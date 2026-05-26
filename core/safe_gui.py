"""
S.P.A.R.K Safe GUI Control & Computer Use
Handles deterministic desktop interaction with screenshot state hashing and pre/post validation.
"""

import hashlib
import logging
import time
from typing import Any, Tuple, Optional
from PIL import Image

logger = logging.getLogger("SPARK_SAFE_GUI")

# Lazy imports for optional GUI libraries
pyautogui = None
mss = None

def _initialize_libraries():
    global pyautogui, mss
    if pyautogui is None:
        try:
            import pyautogui as pg
            pyautogui = pg
            # Safety checks for PyAutoGUI
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
        except ImportError:
            logger.warning("pyautogui not installed or unavailable. Using simulated interface.")
    
    if mss is None:
        try:
            import mss as m
            mss = m
        except ImportError:
            logger.warning("mss not installed or unavailable. Falling back to PIL ImageGrab.")

class SafeGUIPipeline:
    """Manages secure desktop operations with cryptographic screen state checks."""
    
    def __init__(self, use_simulation: bool = False):
        _initialize_libraries()
        self.use_simulation = use_simulation
        # In simulation mode, we maintain a mock state dictionary of coordinates/hashes
        self.mock_screen_state = "initial_base_state_hash_00000"
        self.mock_click_history = []
    
    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """Capture the screen or a specific region (left, top, right, bottom)."""
        if self.use_simulation or (pyautogui is None and mss is None):
            # Return a blank mock image
            return Image.new("RGB", (1920, 1080), color=(0, 0, 0))
            
        try:
            # Try MSS for speed
            if mss is not None:
                with mss.mss() as sct:
                    if region:
                        # MSS expects monitor dict: {'left': x, 'top': y, 'width': w, 'height': h}
                        monitor = {
                            "left": region[0],
                            "top": region[1],
                            "width": region[2] - region[0],
                            "height": region[3] - region[1]
                        }
                        sct_img = sct.grab(monitor)
                    else:
                        sct_img = sct.grab(sct.monitors[1])
                    return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            # Fallback to PIL ImageGrab (built-in Windows support)
            from PIL import ImageGrab
            return ImageGrab.grab(bbox=region)
        except Exception as e:
            logger.error(f"Failed to capture screen: {e}. Returning fallback mock image.")
            return Image.new("RGB", (1920, 1080), color=(0, 0, 0))

    def compute_state_hash(self, img: Image.Image) -> str:
        """Compute the SHA-256 hash of a screen capture to verify layout state."""
        # Resize to lower resolution to prevent minor rendering anti-aliasing issues from breaking checks
        resized = img.resize((256, 256), Image.Resampling.NEAREST)
        img_bytes = resized.tobytes()
        return hashlib.sha256(img_bytes).hexdigest()

    def verify_and_click(
        self, 
        x: int, 
        y: int, 
        expected_pre_hash: Optional[str] = None, 
        expected_post_hash: Optional[str] = None,
        timeout_seconds: float = 2.0
    ) -> Tuple[bool, str, str]:
        """
        Executes a click at (x, y) after checking that the pre-state hash matches.
        Then verifies the post-state hash matches after execution.
        Returns (success_boolean, actual_post_hash, confirmation_token)
        """
        # 1. Pre-state validation
        pre_img = self.capture_screen()
        actual_pre_hash = self.compute_state_hash(pre_img)
        
        if expected_pre_hash and actual_pre_hash != expected_pre_hash:
            logger.error(f"Pre-action state mismatch. Expected: {expected_pre_hash}, Got: {actual_pre_hash}")
            return False, actual_pre_hash, "REJECTED_PRE_STATE_MISMATCH"
            
        # 2. Command execution
        logger.info(f"Executing verified GUI click at coordinate: ({x}, {y})")
        if self.use_simulation or pyautogui is None:
            self.mock_click_history.append((x, y))
            # Simulate state transition
            self.mock_screen_state = hashlib.sha256(f"state_after_click_{x}_{y}".encode()).hexdigest()
        else:
            try:
                pyautogui.click(x, y)
                time.sleep(0.2) # Allow interface to update
            except Exception as e:
                logger.error(f"Failed executing pyautogui click: {e}")
                return False, actual_pre_hash, f"EXECUTION_FAILED: {e}"

        # 3. Post-state validation
        post_img = self.capture_screen()
        actual_post_hash = self.compute_state_hash(post_img) if not self.use_simulation else self.mock_screen_state
        
        if expected_post_hash and actual_post_hash != expected_post_hash:
            # Dynamic retry loop to account for slow UI transitions
            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                time.sleep(0.2)
                post_img = self.capture_screen()
                actual_post_hash = self.compute_state_hash(post_img) if not self.use_simulation else self.mock_screen_state
                if actual_post_hash == expected_post_hash:
                    break
            
            if actual_post_hash != expected_post_hash:
                logger.warning(f"Post-action state mismatch. Expected: {expected_post_hash}, Got: {actual_post_hash}")
                return False, actual_post_hash, "REJECTED_POST_STATE_MISMATCH"

        # Verification token is generated upon successful state-verified execution
        token_payload = f"GUI_CONFIRMED_{x}_{y}_{actual_post_hash}"
        token = hashlib.sha256(token_payload.encode()).hexdigest()
        
        return True, actual_post_hash, token

    def verify_and_type(
        self, 
        text: str, 
        expected_post_hash: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Executes secure typing automation, checking the post-state transition."""
        logger.info(f"Executing typing verification pipeline for input text segment")
        if self.use_simulation or pyautogui is None:
            self.mock_screen_state = hashlib.sha256(f"state_after_type_{text[:10]}".encode()).hexdigest()
        else:
            try:
                pyautogui.write(text, interval=0.01)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed executing pyautogui typing: {e}")
                return False, f"EXECUTION_FAILED: {e}"

        post_img = self.capture_screen()
        actual_post_hash = self.compute_state_hash(post_img) if not self.use_simulation else self.mock_screen_state
        
        if expected_post_hash and actual_post_hash != expected_post_hash:
            return False, f"REJECTED_POST_STATE_MISMATCH: {actual_post_hash}"
            
        return True, actual_post_hash
