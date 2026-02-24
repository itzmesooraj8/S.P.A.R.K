from dataclasses import dataclass, field
from typing import Literal, List, Dict, Optional

NodeType = Literal["module", "class", "function"]
EdgeType = Literal["calls", "imports", "inherits"]

@dataclass
class CodeNode:
    id: str  # Fully qualified: my_module.MyClass.my_function
    type: NodeType
    path: str
    signature: str = ""
    start_line: int = 0
    end_line: int = 0

@dataclass
class CodeEdge:
    source: str
    target: str
    relation: EdgeType

class CodeGraph:
    def __init__(self):
        self.nodes: Dict[str, CodeNode] = {}
        self.edges: List[CodeEdge] = []
        
        # Structural Delta Tracking
        self.delta_nodes_added = 0
        self.delta_nodes_removed = 0
        self.delta_edges_added = 0
        self.delta_edges_removed = 0

    def reset_delta(self):
        self.delta_nodes_added = 0
        self.delta_nodes_removed = 0
        self.delta_edges_added = 0
        self.delta_edges_removed = 0

    def get_delta(self) -> Dict[str, int]:
        return {
            "nodes_added": self.delta_nodes_added,
            "nodes_removed": self.delta_nodes_removed,
            "edges_added": self.delta_edges_added,
            "edges_removed": self.delta_edges_removed
        }

    def remove_file_data(self, file_path: str):
        nodes_to_remove = set([node_id for node_id, node in self.nodes.items() if getattr(node, 'path', '') == file_path])
        if not nodes_to_remove:
            return
            
        for node_id in nodes_to_remove:
            del self.nodes[node_id]
            self.delta_nodes_removed += 1
            
        initial_edges = len(self.edges)
        self.edges = [
            e for e in self.edges 
            if e.source not in nodes_to_remove and e.target not in nodes_to_remove
        ]
        self.delta_edges_removed += (initial_edges - len(self.edges))

    def add_node(self, node: CodeNode):
        if node.id not in self.nodes:
            self.nodes[node.id] = node
            self.delta_nodes_added += 1

    def add_edge(self, source: str, target: str, relation: EdgeType):
        self.edges.append(CodeEdge(source=source, target=target, relation=relation))
        self.delta_edges_added += 1

    def clear(self):
        self.nodes.clear()
        self.edges.clear()

    def get_node(self, node_id: str) -> Optional[CodeNode]:
        return self.nodes.get(node_id)

    def get_dependencies(self, node_id: str) -> List[str]:
        deps = set([e.target for e in self.edges if e.source == node_id])
        return sorted(list(deps))

    def get_callers(self, node_id: str) -> List[str]:
        callers = set([e.source for e in self.edges if e.target == node_id])
        return sorted(list(callers))

    def to_dict(self) -> dict:
        return {
            "nodes": [n.__dict__ for n in self.nodes.values()],
            "edges": [e.__dict__ for e in self.edges]
        }
