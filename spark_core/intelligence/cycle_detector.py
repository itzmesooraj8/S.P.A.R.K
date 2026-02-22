from typing import Dict, List, Set

def detect_cycles(graph: Dict[str, List[str]]) -> int:
    """
    Detects the number of strongly connected components (size > 1) 
    in a directed graph to identify circular dependencies.
    """
    index = 0
    stack: List[str] = []
    indices: Dict[str, int] = {}
    lowlinks: Dict[str, int] = {}
    on_stack: Set[str] = set()
    cycles = 0

    def strongconnect(node: str):
        nonlocal index, cycles
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in indices:
                strongconnect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[neighbor])

        if lowlinks[node] == indices[node]:
            component = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.append(w)
                if w == node:
                    break
            if len(component) > 1:
                cycles += 1

    for node in graph:
        if node not in indices:
            strongconnect(node)

    return cycles
