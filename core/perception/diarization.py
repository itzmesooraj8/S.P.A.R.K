from __future__ import annotations

import numpy as np

class AmbientConversationFilter:
    def __init__(self, target_speaker_id: int = 0, relevance_threshold: float = 0.65):
        self.target_speaker_id = target_speaker_id
        self.relevance_threshold = relevance_threshold

    def diarize_and_route(self, speaker_embeddings: np.ndarray) -> np.ndarray:
        """
        Runs Spectral Clustering to split vocal signals into speaker identities.
        Returns predicted labels for speaker turns.
        """
        # Ensure correct input dimensional shape
        if len(speaker_embeddings) < 2:
            return np.zeros(len(speaker_embeddings), dtype=int)
            
        # Basic spectral clustering implementation on distance similarity matrix
        similarity = np.dot(speaker_embeddings, speaker_embeddings.T)
        degrees = np.diag(np.sum(similarity, axis=1))
        laplacian = degrees - similarity
        
        # Get eigenvalues and eigenvectors
        eigenvals, eigenvecs = np.linalg.eigh(laplacian)
        # Use Fiedler vector coordinates to divide clusters
        labels = (eigenvecs[:, 1] > 0).astype(int)
        return labels
