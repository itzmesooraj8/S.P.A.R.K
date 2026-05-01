import os
import logging
from thefuzz import process
import platform

logger = logging.getLogger("SPARK_FILE_OPS")

def get_search_directories():
    """Returns the absolute paths of Desktop, Documents, and Downloads."""
    home = os.path.expanduser("~")
    dirs = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "Documents"),
        os.path.join(home, "Downloads")
    ]
    return [d for d in dirs if os.path.exists(d)]

def search_and_open_file(query: str) -> str:
    """Fuzzy searches for a file and opens the best match."""
    logger.info(f"Fuzzy searching for file: {query}")
    search_dirs = get_search_directories()
    
    all_files = {}
    
    # Gather all files in these directories (top level + 1 level deep to avoid hanging)
    for d in search_dirs:
        try:
            for root, dirs, files in os.walk(d):
                depth = root[len(d):].count(os.sep)
                if depth > 1:
                    dirs.clear() # Don't go too deep
                for f in files:
                    # Ignore common hidden/system files
                    if not f.startswith('.') and not f.startswith('~'):
                        all_files[f] = os.path.join(root, f)
        except Exception as e:
            logger.warning(f"Error reading directory {d}: {e}")
            
    if not all_files:
        return "I could not access any files to search, sir."
        
    file_names = list(all_files.keys())
    
    # Use thefuzz to find the best match
    best_match = process.extractOne(query, file_names)
    
    if best_match and best_match[1] > 60: # Score threshold
        target_name = best_match[0]
        target_path = all_files[target_name]
        
        try:
            if platform.system() == 'Windows':
                os.startfile(target_path)
            elif platform.system() == 'Darwin':
                os.system(f'open "{target_path}"')
            else:
                os.system(f'xdg-open "{target_path}"')
                
            return f"Opening {target_name}, sir."
        except Exception as e:
            logger.error(f"Error opening file {target_path}: {e}")
            return f"I found {target_name}, but encountered an error opening it."
            
    return f"I could not find any files matching '{query}' in your personal folders, sir."
