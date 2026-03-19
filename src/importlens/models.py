from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class EvidenceType(StrEnum):
    MEASURED = "measured"
    INFERRED = "inferred"
    HEURISTIC = "heuristic"


class TargetKind(StrEnum):
    SCRIPT = "script"
    PACKAGE = "package"
    MODULE = "module"


@dataclass(frozen=True, slots=True)
class TargetSpec:
    raw_target: str
    target_kind: TargetKind
    resolved_path: Path | None
    package_root: Path | None
    internal_prefixes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TimingRecord:
    module_name: str
    self_time_us: int
    cumulative_time_us: int
    import_depth: int
    source: EvidenceType = EvidenceType.MEASURED


@dataclass(frozen=True, slots=True)
class ParseAnomaly:
    line_number: int
    content: str
    message: str


@dataclass(frozen=True, slots=True)
class ModuleNode:
    module_name: str
    file_path: Path
    is_internal: bool
    is_resolved: bool


@dataclass(frozen=True, slots=True)
class ImportLocation:
    file_path: Path
    line_number: int


@dataclass(frozen=True, slots=True)
class ImportEdge:
    importer: str
    imported: str
    import_kind: str
    location: ImportLocation
    is_resolved: bool
    source: EvidenceType = EvidenceType.INFERRED


@dataclass(frozen=True, slots=True)
class CycleFinding:
    modules: tuple[str, ...]
    edge_locations: tuple[ImportLocation, ...]
    source: EvidenceType = EvidenceType.INFERRED


@dataclass(frozen=True, slots=True)
class StaticAnalysisResult:
    target: TargetSpec
    module_nodes: tuple[ModuleNode, ...]
    import_edges: tuple[ImportEdge, ...]
    cycles: tuple[CycleFinding, ...]
    limitations: tuple[str, ...]
    unresolved_imports: tuple[ImportEdge, ...] = ()


@dataclass(frozen=True, slots=True)
class Finding:
    kind: str
    title: str
    summary: str
    evidence_type: EvidenceType
    confidence_note: str
    related_modules: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CombinedReport:
    target: TargetSpec
    profile_result: object | None
    static_result: StaticAnalysisResult
    findings: tuple[Finding, ...]
    limitations: tuple[str, ...]
