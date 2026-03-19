from __future__ import annotations

from collections import defaultdict

from importlens.models import CycleFinding, ImportEdge, ImportLocation


def build_adjacency(edges: tuple[ImportEdge, ...]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge.is_resolved:
            adjacency[edge.importer].add(edge.imported)
    return dict(adjacency)


def detect_cycles(edges: tuple[ImportEdge, ...]) -> tuple[CycleFinding, ...]:
    adjacency = build_adjacency(edges)
    location_by_pair: dict[tuple[str, str], ImportLocation] = {
        (edge.importer, edge.imported): edge.location for edge in edges if edge.is_resolved
    }

    seen_cycles: set[tuple[str, ...]] = set()
    found: list[CycleFinding] = []

    def visit(node: str, path: list[str], visiting: set[str]) -> None:
        path.append(node)
        visiting.add(node)
        for neighbor in adjacency.get(node, set()):
            if neighbor in visiting:
                start_index = path.index(neighbor)
                cycle_path = path[start_index:] + [neighbor]
                canonical = canonicalize_cycle(cycle_path)
                if canonical not in seen_cycles:
                    seen_cycles.add(canonical)
                    locations = tuple(
                        location_by_pair[(cycle_path[index], cycle_path[index + 1])]
                        for index in range(len(cycle_path) - 1)
                        if (cycle_path[index], cycle_path[index + 1]) in location_by_pair
                    )
                    found.append(
                        CycleFinding(
                            modules=tuple(cycle_path),
                            edge_locations=locations,
                        )
                    )
            elif neighbor not in path:
                visit(neighbor, path.copy(), visiting.copy())

    for node in adjacency:
        visit(node, [], set())
    return tuple(sorted(found, key=lambda cycle: cycle.modules))


def canonicalize_cycle(cycle_path: list[str]) -> tuple[str, ...]:
    cycle_body = cycle_path[:-1]
    rotations = [
        tuple(cycle_body[index:] + cycle_body[:index] + [cycle_body[index]])
        for index in range(len(cycle_body))
    ]
    return min(rotations)
