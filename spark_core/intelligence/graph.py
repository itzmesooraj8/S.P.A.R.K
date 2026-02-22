from dataclasses import dataclass, field
from typing import Literal, List, Dict, Optional
from system.state import unified_state

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

    def _sync(self):
        unified_state.update("code_graph", self.to_dict())

    def add_node(self, node: CodeNode):
        if node.id not in self.nodes:
            self.nodes[node.id] = node
            self._sync()

    def add_edge(self, source: str, target: str, relation: EdgeType):
        self.edges.append(CodeEdge(source=source, target=target, relation=relation))
        self._sync()

    def clear(self):
        self.nodes.clear()
        self.edges.clear()
        self._sync()

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
