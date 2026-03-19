from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from importlens.config import AnalysisConfig
from importlens.graph import detect_cycles
from importlens.models import (
    ImportEdge,
    ImportLocation,
    ModuleNode,
    StaticAnalysisResult,
    TargetKind,
    TargetSpec,
)
from importlens.runtime import ProfileError, is_url_target


@dataclass(frozen=True, slots=True)
class ModuleSource:
    module_name: str
    file_path: Path


def resolve_static_target(raw_target: str, working_directory: Path) -> TargetSpec:
    if is_url_target(raw_target):
        raise ProfileError("Unsupported target: URLs are not accepted.")

    candidate_path = (working_directory / raw_target).resolve()
    if not candidate_path.exists():
        raise ProfileError(f"Unsupported target: path does not exist: {raw_target}")
    if candidate_path.is_file():
        if candidate_path.suffix != ".py":
            raise ProfileError(
                "Unsupported target: expected a Python source file or "
                "package directory."
            )
        package_root = candidate_path.parent
        internal_prefixes = discover_package_prefixes(package_root)
        return TargetSpec(
            raw_target=raw_target,
            target_kind=TargetKind.SCRIPT,
            resolved_path=candidate_path,
            package_root=package_root,
            internal_prefixes=internal_prefixes,
        )
    if candidate_path.is_dir():
        python_files = list(candidate_path.rglob("*.py"))
        if not python_files:
            raise ProfileError("Unsupported target: package directory contains no Python files.")
        return TargetSpec(
            raw_target=raw_target,
            target_kind=TargetKind.PACKAGE,
            resolved_path=candidate_path,
            package_root=candidate_path.parent,
            internal_prefixes=(candidate_path.name,),
        )
    raise ProfileError("Unsupported target: target path is neither a file nor a directory.")


def discover_package_prefixes(root: Path) -> tuple[str, ...]:
    prefixes: list[str] = []
    for child in root.iterdir():
        if child.is_dir() and (child / "__init__.py").is_file():
            prefixes.append(child.name)
    if not prefixes:
        return ()
    return tuple(sorted(prefixes))


def collect_module_sources(target: TargetSpec) -> tuple[ModuleSource, ...]:
    root = source_discovery_root(target)
    module_root = module_naming_root(target)
    python_files = sorted(root.rglob("*.py"))
    sources: list[ModuleSource] = []
    for file_path in python_files:
        if "__pycache__" in file_path.parts:
            continue
        module_name = module_name_from_path(file_path, module_root)
        sources.append(ModuleSource(module_name=module_name, file_path=file_path))
    return tuple(sources)


def source_discovery_root(target: TargetSpec) -> Path:
    if target.resolved_path is not None and target.resolved_path.is_dir():
        return target.resolved_path
    assert target.package_root is not None
    return target.package_root


def module_naming_root(target: TargetSpec) -> Path:
    assert target.package_root is not None
    return target.package_root


def module_name_from_path(file_path: Path, root: Path) -> str:
    relative = file_path.relative_to(root)
    parts = list(relative.parts)
    if parts[-1] == "__init__.py":
        module_parts = parts[:-1] + ["__init__"]
    else:
        module_parts = parts[:-1] + [file_path.stem]
    return ".".join(module_parts)


def module_base_name(module_name: str) -> str:
    if module_name.endswith(".__init__"):
        return module_name[: -len(".__init__")]
    return module_name


def build_module_index(sources: tuple[ModuleSource, ...]) -> dict[str, ModuleSource]:
    index: dict[str, ModuleSource] = {}
    for source in sources:
        index[source.module_name] = source
        base_name = module_base_name(source.module_name)
        index.setdefault(base_name, source)
    return index


def parse_import_edges(
    source: ModuleSource,
    module_index: dict[str, ModuleSource],
) -> tuple[ImportEdge, ...]:
    tree = ast.parse(source.file_path.read_text(encoding="utf-8"), filename=str(source.file_path))
    edges: list[ImportEdge] = []
    current_package = relative_import_context(source.module_name)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported = alias.name
                resolved_module = resolve_static_import(imported, current_package, 0, module_index)
                edges.append(
                    ImportEdge(
                        importer=source.module_name,
                        imported=resolved_module or imported,
                        import_kind="import",
                        location=ImportLocation(source.file_path, node.lineno),
                        is_resolved=resolved_module is not None,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    imported = module_name
                elif module_name:
                    imported = f"{module_name}.{alias.name}"
                else:
                    imported = alias.name
                resolved_module = resolve_static_import(
                    imported,
                    current_package,
                    node.level,
                    module_index,
                )
                edges.append(
                    ImportEdge(
                        importer=source.module_name,
                        imported=resolved_module or imported,
                        import_kind="from",
                        location=ImportLocation(source.file_path, node.lineno),
                        is_resolved=resolved_module is not None,
                    )
                )
    return tuple(edges)


def resolve_static_import(
    imported: str,
    current_package: str,
    level: int,
    module_index: dict[str, ModuleSource],
) -> str | None:
    candidates: list[str] = []
    normalized_import = imported.strip(".")

    if level > 0:
        package_parts = [part for part in current_package.split(".") if part]
        if level > len(package_parts):
            return None
        base_parts = package_parts[: len(package_parts) - level + 1]
        if normalized_import:
            qualified = ".".join(base_parts + normalized_import.split("."))
            candidates.extend(expand_module_candidates(qualified))
        else:
            candidates.append(".".join(base_parts))
    elif normalized_import:
        candidates.extend(expand_module_candidates(normalized_import))

    deduped = [
        candidate
        for index, candidate in enumerate(candidates)
        if candidate and candidate not in candidates[:index]
    ]
    for candidate in deduped:
        if candidate in module_index:
            return candidate
    return None


def relative_import_context(module_name: str) -> str:
    base_name = module_base_name(module_name)
    if module_name.endswith(".__init__"):
        return base_name
    if "." in base_name:
        return base_name.rsplit(".", maxsplit=1)[0]
    return base_name


def expand_module_candidates(qualified_name: str) -> tuple[str, ...]:
    parts = qualified_name.split(".")
    candidates = [".".join(parts[:index]) for index in range(len(parts), 0, -1)]
    return tuple(candidate for candidate in candidates if candidate)


def filter_import_edges(
    edges: tuple[ImportEdge, ...],
    config: AnalysisConfig,
    internal_prefixes: tuple[str, ...],
) -> tuple[ImportEdge, ...]:
    filtered = list(edges)
    if config.include:
        filtered = [
            edge
            for edge in filtered
            if any(
                pattern in edge.importer or pattern in edge.imported
                for pattern in config.include
            )
        ]
    if config.exclude:
        filtered = [
            edge
            for edge in filtered
            if not any(
                pattern in edge.importer or pattern in edge.imported
                for pattern in config.exclude
            )
        ]
    if config.internal_only and internal_prefixes:
        filtered = [
            edge
            for edge in filtered
            if any(
                (
                    edge.importer == prefix
                    or edge.importer.startswith(f"{prefix}.")
                    or edge.imported == prefix
                    or edge.imported.startswith(f"{prefix}.")
                )
                for prefix in internal_prefixes
            )
        ]
    return tuple(filtered)


def deduplicate_import_edges(edges: tuple[ImportEdge, ...]) -> tuple[ImportEdge, ...]:
    deduped: list[ImportEdge] = []
    seen: set[tuple[str, str, str, Path, int, bool]] = set()
    for edge in edges:
        key = (
            edge.importer,
            edge.imported,
            edge.import_kind,
            edge.location.file_path,
            edge.location.line_number,
            edge.is_resolved,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(edge)
    return tuple(deduped)


def build_module_nodes(
    sources: tuple[ModuleSource, ...],
    internal_prefixes: tuple[str, ...],
) -> tuple[ModuleNode, ...]:
    nodes: list[ModuleNode] = []
    for source in sources:
        nodes.append(
            ModuleNode(
                module_name=source.module_name,
                file_path=source.file_path,
                is_internal=any(
                    source.module_name == prefix or source.module_name.startswith(f"{prefix}.")
                    for prefix in internal_prefixes
                )
                if internal_prefixes
                else True,
                is_resolved=True,
            )
        )
    return tuple(nodes)


def analyze_static_target(
    raw_target: str,
    config: AnalysisConfig,
    working_directory: Path,
) -> StaticAnalysisResult:
    target = resolve_static_target(raw_target, working_directory=working_directory)
    sources = collect_module_sources(target)
    module_index = build_module_index(sources)
    nodes = build_module_nodes(sources, internal_prefixes=target.internal_prefixes)
    all_edges = tuple(
        edge
        for source in sources
        for edge in parse_import_edges(source, module_index)
    )
    filtered_edges = filter_import_edges(
        all_edges,
        config=config,
        internal_prefixes=target.internal_prefixes,
    )
    filtered_edges = deduplicate_import_edges(filtered_edges)
    unresolved = tuple(edge for edge in filtered_edges if not edge.is_resolved)
    limitations: list[str] = []
    if unresolved:
        limitations.append(
            "Some imports could not be resolved statically and are reported as unresolved."
        )
    cycles = detect_cycles(filtered_edges)
    return StaticAnalysisResult(
        target=target,
        module_nodes=nodes,
        import_edges=filtered_edges,
        cycles=cycles,
        limitations=tuple(limitations),
        unresolved_imports=unresolved,
    )
