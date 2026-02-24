class ASTCache:
    def __init__(self):
        self.cache = {}

    def store(self, path: str, ast_tree):
        self.cache[path] = ast_tree

    def get(self, path: str):
        return self.cache.get(path)

    def remove(self, path: str):
        if path in self.cache:
            del self.cache[path]
