import os
import hashlib
from spark.modules.memory import memory_engine

class KnowledgeScanner:
    def __init__(self, knowledge_dir="./knowledge_base"):
        self.knowledge_dir = knowledge_dir
        self.processed_files_cache = {} # path: hash
        if not os.path.exists(self.knowledge_dir):
            os.makedirs(self.knowledge_dir)
            print(f"[SCANNER] Created knowledge base directory at {self.knowledge_dir}")

    def get_file_hash(self, filepath):
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def scan(self):
        """
        Walks through the knowledge_base directory and ingests new or changed files.
        """
        print("[SCANNER] Starting deep scan of knowledge base...")
        files_found = 0
        for root, dirs, files in os.walk(self.knowledge_dir):
            for file in files:
                filepath = os.path.join(root, file)
                file_hash = self.get_file_hash(filepath)
                
                if self.processed_files_cache.get(filepath) != file_hash:
                    self.ingest_file(filepath)
                    self.processed_files_cache[filepath] = file_hash
                    files_found += 1
        
        print(f"[SCANNER] Scan complete. Ingested {files_found} new/updated files.")

    def ingest_file(self, filepath):
        """
        Reads a file and breaks it into chunks for memory storage.
        """
        ext = os.path.splitext(filepath)[1].lower()
        content = ""
        
        try:
            if ext in [".txt", ".md", ".py"]:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif ext == ".pdf":
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(filepath)
                    content = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
                except ImportError:
                    print("[SCANNER] pypdf not installed. Skipping PDF.")
                    return
            
            if content:
                # Basic chunking by paragraphs or sentences
                chunks = content.split("\n\n")
                for i, chunk in enumerate(chunks):
                    if len(chunk.strip()) > 10:
                        memory_engine.add_memory(
                            chunk.strip(), 
                            {"source": filepath, "chunk": i}
                        )
                print(f"[SCANNER] Ingested {filepath}")
        except Exception as e:
            print(f"[SCANNER] Failed to ingest {filepath}: {e}")

# Singleton scanner
scanner = KnowledgeScanner()

if __name__ == "__main__":
    # Test scan
    scanner.scan()
