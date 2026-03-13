class CitationStore:
    """
    Tracks every source referenced during deep research.
    """
    def __init__(self):
        self.citations = {}
        self.counter = 1

    def add_citation(self, title: str, url: str, snippet: str) -> int:
        idx = self.counter
        self.citations[idx] = {"title": title, "url": url, "snippet": snippet}
        self.counter += 1
        return idx

    def get_citations(self) -> dict:
        return self.citations

    def clear(self):
        self.citations = {}
        self.counter = 1

citation_store = CitationStore()
