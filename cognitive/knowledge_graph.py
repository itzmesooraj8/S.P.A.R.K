from __future__ import annotations

import networkx as nx

class LocalKnowledgeGraph:
    """Zero-cost local directed graph database establishing relations between entities and systems."""
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_relationship(self, entity_a: str, relationship: str, entity_b: str):
        self.graph.add_edge(entity_a.lower(), entity_b.lower(), type=relationship.lower())

    def get_connected_entities(self, entity: str) -> list[dict]:
        clean = entity.lower()
        if not self.graph.has_node(clean):
            return []
        
        connections = []
        for target in self.graph.successors(clean):
            edge_data = self.graph.get_edge_data(clean, target)
            connections.append({
                "target": target,
                "relationship": edge_data.get("type", "related_to")
            })
        return connections
