from __future__ import annotations

import numpy as np

class ComponentSpectralMatcher:
    """Matches localized spatial crop signatures to hardware inventory embedding catalogs."""
    def __init__(self):
        # Anchor embeddings mapping: Name -> 4-dim unit vector
        self.catalog = {
            "IC_NE555": np.array([0.15, 0.82, -0.44, 0.03]),
            "CAP_10UF": np.array([-0.72, 0.11, 0.32, 0.51]),
            "RES_10K": np.array([0.45, -0.42, 0.61, 0.12])
        }

    def match_component(self, crop: np.ndarray) -> tuple[str, float]:
        if crop.size == 0:
            return "unknown", 0.0
            
        # Simplified local spatial intensity signature mapping
        h, w = crop.shape[:2]
        regions = [
            crop[0:h//2, 0:w//2],
            crop[0:h//2, w//2:w],
            crop[h//2:h, 0:w//2],
            crop[h//2:h, w//2:w]
        ]
        embedding = np.array([np.mean(r) for r in regions])
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        # Match using cosine similarity
        best_name = "unknown"
        best_sim = -1.0
        
        for name, anchor in self.catalog.items():
            denom = np.linalg.norm(embedding) * np.linalg.norm(anchor)
            if denom == 0:
                continue
            sim = np.dot(embedding, anchor) / denom
            if sim > best_sim:
                best_sim = sim
                best_name = name

        return best_name, float(best_sim)
