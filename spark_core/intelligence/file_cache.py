import os
import hashlib
from typing import Dict, Tuple

class FileHashCache:
    def __init__(self):
        # path -> (mtime, size, sha256)
        self.hashes: Dict[str, Tuple[float, int, str]] = {}

    def has_changed(self, file_path: str) -> bool:
        try:
            stat = os.stat(file_path)
            mtime = stat.st_mtime
            size = stat.st_size
        except OSError:
            return True # If we can't stat it, assume changed or deleted
            
        old_data = self.hashes.get(file_path)
        if old_data and old_data[0] == mtime and old_data[1] == size:
            return False
            
        # If mtime or size changed, compute SHA256
        new_hash = self.compute_hash(file_path)
        
        if old_data and old_data[2] == new_hash:
            # File modified but content identical
            self.hashes[file_path] = (mtime, size, new_hash)
            return False
            
        self.hashes[file_path] = (mtime, size, new_hash)
        return True
        
    def compute_hash(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            return hashlib.sha256(data).hexdigest()
        except OSError:
            return ""

    def remove(self, file_path: str):
        if file_path in self.hashes:
            del self.hashes[file_path]
