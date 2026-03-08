"""
SPARK Knowledge Base File Watcher
────────────────────────────────────────────────────────────────────────────────
Monitors /knowledge_base/ directory for new or modified documents.
Automatically indexes them into ChromaDB without requiring server restart.
Uses watchdog for efficient file system event detection.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Set

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

# Import the indexing function
from neural_search.search import index_document, IndexRequest


class KnowledgeBaseHandler(FileSystemEventHandler):
    """Watches /knowledge_base/ and indexes files on create/modify."""

    def __init__(self):
        self.kb_path = Path(__file__).parent.parent.parent / "knowledge_base"
        self.indexed_files: Set[str] = set()
        self._indexing_lock = asyncio.Lock()

    def on_created(self, event: FileCreatedEvent):
        """Handle new files."""
        if event.is_directory or self._should_ignore(event.src_path):
            return
        asyncio.create_task(self._index_file(event.src_path))

    def on_modified(self, event: FileModifiedEvent):
        """Handle modified files."""
        if event.is_directory or self._should_ignore(event.src_path):
            return
        asyncio.create_task(self._index_file(event.src_path))

    def _should_ignore(self, path: str) -> bool:
        """Skip hidden files, temp files, and non-text formats."""
        name = Path(path).name
        return (
            name.startswith(".")
            or name.startswith("~")
            or name.endswith((".tmp", ".lock", ".bak"))
        )

    async def _index_file(self, file_path: str):
        """Index a file into ChromaDB asynchronously."""
        async with self._indexing_lock:
            try:
                path = Path(file_path)
                if not path.exists() or not path.is_file():
                    return

                # Skip if already indexed recently
                if file_path in self.indexed_files:
                    return

                # Read file content
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception:
                    return

                if not content.strip():
                    return

                # Create index request
                doc_id = f"kb_{path.stem}_{int(path.stat().st_mtime)}"
                rel_path = path.relative_to(self.kb_path)

                req = IndexRequest(
                    text=content,
                    collection="spark_knowledge",
                    doc_id=doc_id,
                    metadata={
                        "source": str(rel_path),
                        "file_path": file_path,
                        "file_size_bytes": path.stat().st_size,
                    },
                    tags=["knowledge_base", path.suffix.lstrip(".")],
                )

                # Index via the API function
                await index_document(req)
                self.indexed_files.add(file_path)
                print(f"📚 [KB Watch] Indexed: {rel_path}")

            except Exception as e:
                print(f"⚠️ [KB Watch] Error indexing {file_path}: {e}")


class KnowledgeBaseWatcher:
    """Background file system watcher for the knowledge base directory."""

    def __init__(self):
        self.kb_path = Path(__file__).parent.parent.parent / "knowledge_base"
        self.observer: Optional[Observer] = None
        self.handler: Optional[KnowledgeBaseHandler] = None

    def start(self):
        """Start watching the knowledge_base directory."""
        if self.observer is not None:
            return

        # Create directory if it doesn't exist
        self.kb_path.mkdir(parents=True, exist_ok=True)

        self.handler = KnowledgeBaseHandler()
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.kb_path), recursive=True)
        self.observer.start()

        print(f"📚 [KB Watch] Started monitoring {self.kb_path}")

        # Index existing files on startup
        asyncio.create_task(self._index_existing_files())

    async def _index_existing_files(self):
        """Index all existing files in knowledge_base on startup."""
        try:
            for file_path in self.kb_path.glob("**/*"):
                if file_path.is_file() and not self.handler._should_ignore(str(file_path)):
                    await self.handler._index_file(str(file_path))
            print(f"📚 [KB Watch] Startup indexing complete")
        except Exception as e:
            print(f"⚠️ [KB Watch] Startup indexing error: {e}")

    def stop(self):
        """Stop watching and clean up."""
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None
            print("📚 [KB Watch] Stopped")


# Singleton watcher instance
kb_watcher = KnowledgeBaseWatcher()
