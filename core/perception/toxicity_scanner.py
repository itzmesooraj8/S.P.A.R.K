from __future__ import annotations

import numpy as np

class OpticalToxicityScanner:
    """Evaluates targeted color spectrum variance to detect cell stress, yellowing, or decay."""
    def evaluate_chromatic_shift(self, image: np.ndarray) -> float:
        if image.size == 0:
            return 0.0
            
        mean_r = np.mean(image[..., 2])
        mean_g = np.mean(image[..., 1])
        mean_b = np.mean(image[..., 0])
        
        if mean_b == 0:
            return 0.0
            
        # Yellow ratio: (R + G) / (2 * B)
        yellow_ratio = (mean_r + mean_g) / (2.0 * mean_b + 1.0)
        toxicity_index = (yellow_ratio - 1.0) / 2.0
        
        return float(np.clip(toxicity_index, 0.0, 1.0))
