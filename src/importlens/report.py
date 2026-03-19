from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from importlens.config import AnalysisConfig
from importlens.models import CombinedReport, EvidenceType, Finding, StaticAnalysisResult
from importlens.runtime import ProfileError, ProfileResult, profile_target, summarize_timing_records
from importlens.static import analyze_static_target


def render_profile_text(result: ProfileResult) -> str:
    summary_records = summarize_timing_records(
        result.timing_records,
        internal_prefixes=result.target.internal_prefixes,
    )
    lines = [
        "importlens profile",
        f"target: {result.target.raw_target}",
        f"target_type: {result.target.target_kind.value}",
        "limitations:",
    ]
    lines.extend(f"- {limitation}" for limitation in result.limitations)
    if result.parse_anomalies:
        lines.append("parse_anomalies:")
        for anomaly in result.parse_anomalies:
            lines.append(
                f"- line {anomaly.line_number}: {anomaly.message} | content={anomaly.content}"
            )
    lines.append("summary_records:")
    if not summary_records:
        lines.append("- no timing records matched the active filters")
        return "\n".join(lines)

    for record in summary_records:
        lines.append(
            "  - "
            f"{record.module_name}: self={record.self_time_us}us, "
            f"cumulative={record.cumulative_time_us}us, "
            f"depth={record.import_depth}, evidence={record.source.value}"
        )
    return "\n".join(lines)


def render_profile_json(result: ProfileResult) -> str:
    payload = {
        "target": {
            "raw_target": result.target.raw_target,
            "target_kind": result.target.target_kind.value,
            "resolved_path": (
                str(result.target.resolved_path)
                if result.target.resolved_path is not None
                else None
            ),
            "package_root": (
                str(result.target.package_root)
                if result.target.package_root is not None
                else None
            ),
            "internal_prefixes": list(result.target.internal_prefixes),
        },
        "limitations": list(result.limitations),
        "parse_anomalies": [
            {
                "line_number": anomaly.line_number,
                "content": anomaly.content,
                "message": anomaly.message,
            }
            for anomaly in result.parse_anomalies
        ],
        "timing_records": [
            {
                "module_name": record.module_name,
                "self_time_us": record.self_time_us,
                "cumulative_time_us": record.cumulative_time_us,
                "import_depth": record.import_depth,
                "source": record.source.value,
            }
            for record in result.timing_records
        ],
        "summary_records": [
            {
                "module_name": record.module_name,
                "self_time_us": record.self_time_us,
                "cumulative_time_us": record.cumulative_time_us,
                "import_depth": record.import_depth,
                "source": record.source.value,
            }
            for record in summarize_timing_records(
                result.timing_records,
                internal_prefixes=result.target.internal_prefixes,
            )
        ],
    }
    return json.dumps(payload, indent=2)


def render_graph_text(result: StaticAnalysisResult) -> str:
    visible_nodes = sorted(result.module_nodes, key=lambda item: item.module_name)
    visible_edges = sorted(result.import_edges, key=lambda item: (item.importer, item.imported))
    node_limit = 12
    edge_limit = 15

    lines = [
        "importlens graph",
        f"target: {result.target.raw_target}",
        f"target_type: {result.target.target_kind.value}",
        f"node_count: {len(result.module_nodes)}",
        f"edge_count: {len(result.import_edges)}",
    ]
    if result.limitations:
        lines.append("limitations:")
        lines.extend(f"- {limitation}" for limitation in result.limitations)
    lines.append("nodes:")
    for node in visible_nodes[:node_limit]:
        lines.append(f"  - {node.module_name}")
    if len(visible_nodes) > node_limit:
        lines.append(
            f"  - ... {len(visible_nodes) - node_limit} more nodes omitted from text output"
        )
    lines.append("edges:")
    for edge in visible_edges[:edge_limit]:
        status = "resolved" if edge.is_resolved else "unresolved"
        lines.append(
            f"  - {edge.importer} -> {edge.imported} "
            f"({status}, line={edge.location.line_number}, evidence={edge.source.value})"
        )
    if len(visible_edges) > edge_limit:
        lines.append(
            f"  - ... {len(visible_edges) - edge_limit} more edges omitted from text output"
        )
    return "\n".join(lines)


def render_graph_json(result: StaticAnalysisResult) -> str:
    payload = {
        "target": {
            "raw_target": result.target.raw_target,
            "target_kind": result.target.target_kind.value,
            "resolved_path": (
                str(result.target.resolved_path)
                if result.target.resolved_path is not None
                else None
            ),
            "package_root": (
                str(result.target.package_root)
                if result.target.package_root is not None
                else None
            ),
            "internal_prefixes": list(result.target.internal_prefixes),
        },
        "limitations": list(result.limitations),
        "nodes": [
            {
                "module_name": node.module_name,
                "file_path": str(node.file_path),
                "is_internal": node.is_internal,
                "is_resolved": node.is_resolved,
            }
            for node in sorted(result.module_nodes, key=lambda item: item.module_name)
        ],
        "edges": [
            {
                "importer": edge.importer,
                "imported": edge.imported,
                "import_kind": edge.import_kind,
                "line_number": edge.location.line_number,
                "is_resolved": edge.is_resolved,
                "source": edge.source.value,
            }
            for edge in sorted(result.import_edges, key=lambda item: (item.importer, item.imported))
        ],
        "unresolved_imports": [
            {
                "importer": edge.importer,
                "imported": edge.imported,
                "line_number": edge.location.line_number,
            }
            for edge in result.unresolved_imports
        ],
    }
    return json.dumps(payload, indent=2)


def render_cycles_text(result: StaticAnalysisResult) -> str:
    lines = [
        "importlens cycles",
        f"target: {result.target.raw_target}",
        f"target_type: {result.target.target_kind.value}",
    ]
    if result.limitations:
        lines.append("limitations:")
        lines.extend(f"- {limitation}" for limitation in result.limitations)
    lines.append("cycles:")
    if not result.cycles:
        lines.append("- no cycles found")
        return "\n".join(lines)
    for cycle in result.cycles:
        lines.append(f"  - {' -> '.join(cycle.modules)}")
    return "\n".join(lines)


def render_cycles_json(result: StaticAnalysisResult) -> str:
    payload = {
        "target": {
            "raw_target": result.target.raw_target,
            "target_kind": result.target.target_kind.value,
        },
        "limitations": list(result.limitations),
        "cycles": [
            {
                "modules": list(cycle.modules),
                "edge_locations": [
                    {
                        "file_path": str(location.file_path),
                        "line_number": location.line_number,
                    }
                    for location in cycle.edge_locations
                ],
                "source": cycle.source.value,
            }
            for cycle in result.cycles
        ],
    }
    return json.dumps(payload, indent=2)


def build_combined_report(
    profile_result: ProfileResult | None,
    static_result: StaticAnalysisResult,
) -> CombinedReport:
    findings: list[Finding] = []
    limitations = list(static_result.limitations)
    if profile_result is not None:
        limitations.extend(profile_result.limitations)
        if profile_result.parse_anomalies:
            limitations.append(
                "Some runtime importtime lines were malformed and are reported as parse anomalies."
            )
        summary_records = summarize_timing_records(
            profile_result.timing_records,
            internal_prefixes=profile_result.target.internal_prefixes,
            limit=3,
        )
        for record in summary_records:
            findings.append(
                Finding(
                    kind="slow-import",
                    title=f"Slow import: {record.module_name}",
                    summary=(
                        f"{record.module_name} adds "
                        f"{record.cumulative_time_us}us cumulative import time "
                        "in this environment."
                    ),
                    evidence_type=EvidenceType.MEASURED,
                    confidence_note="Measured at runtime, but environment-dependent.",
                    related_modules=(record.module_name,),
                )
            )

    for cycle in static_result.cycles:
        findings.append(
            Finding(
                kind="cycle",
                title=f"Import cycle: {' -> '.join(cycle.modules)}",
                summary="A static import cycle was detected in the analyzed scope.",
                evidence_type=EvidenceType.INFERRED,
                confidence_note=(
                    "Inferred from static analysis and may not cover "
                    "dynamic import behavior."
                ),
                related_modules=cycle.modules,
            )
        )

    if static_result.unresolved_imports:
        unresolved_modules = tuple(
            sorted({edge.imported for edge in static_result.unresolved_imports})
        )
        findings.append(
            Finding(
                kind="unresolved-import",
                title="Unresolved imports detected",
                summary=(
                    "Some imports could not be resolved statically and "
                    "should be reviewed carefully."
                ),
                evidence_type=EvidenceType.INFERRED,
                confidence_note="Inferred from static analysis and intentionally conservative.",
                related_modules=unresolved_modules,
            )
        )

    import_counts = Counter(
        edge.imported for edge in static_result.import_edges if edge.is_resolved
    )
    for module_name, count in import_counts.most_common(1):
        if count > 1:
            findings.append(
                Finding(
                    kind="dependency-hotspot",
                    title=f"Dependency hotspot: {module_name}",
                    summary=(
                        f"{module_name} is imported by {count} edges in the "
                        "analyzed graph and may be a structural hotspot."
                    ),
                    evidence_type=EvidenceType.HEURISTIC,
                    confidence_note=(
                        "Heuristic based on static graph fan-in, not a "
                        "guaranteed problem."
                    ),
                    related_modules=(module_name,),
                )
            )

    target = profile_result.target if profile_result is not None else static_result.target
    return CombinedReport(
        target=target,
        profile_result=profile_result,
        static_result=static_result,
        findings=tuple(findings),
        limitations=tuple(dict.fromkeys(limitations)),
    )


def derive_report_static_target(profile_result: ProfileResult, working_directory: Path) -> str:
    target = profile_result.target
    if target.target_kind.value == "package":
        raise ProfileError(
            "The report command does not accept package directory targets "
            "until runtime profiling supports them."
        )

    if target.package_root is None or not target.internal_prefixes:
        raise ProfileError(
            "The report command requires a derivable internal package scope for static analysis."
        )

    for prefix in target.internal_prefixes:
        candidate = target.package_root / prefix
        if candidate.is_dir() and any(candidate.rglob("*.py")):
            try:
                return str(candidate.relative_to(working_directory))
            except ValueError:
                return str(candidate)

    raise ProfileError(
        "The report command could not derive a coherent internal package scope from the target."
    )


def analyze_report_target(
    raw_target: str,
    config: AnalysisConfig,
    working_directory: Path,
    runner: Callable[[object], str] | None = None,
) -> CombinedReport:
    profile_result = profile_target(
        raw_target=raw_target,
        config=config,
        working_directory=working_directory,
        runner=runner,
    )
    static_target = derive_report_static_target(profile_result, working_directory=working_directory)
    static_result = analyze_static_target(
        raw_target=static_target,
        config=config,
        working_directory=working_directory,
    )
    combined = build_combined_report(
        profile_result=profile_result,
        static_result=static_result,
    )
    return combined


def render_report_text(result: CombinedReport) -> str:
    lines = [
        "importlens report",
        f"target: {result.target.raw_target}",
        f"target_type: {result.target.target_kind.value}",
    ]
    if result.limitations:
        lines.append("limitations:")
        lines.extend(f"- {limitation}" for limitation in result.limitations)
    lines.append("findings:")
    if not result.findings:
        lines.append("- no actionable findings were produced for this target")
        return "\n".join(lines)
    for finding in result.findings:
        lines.append(
            f"- [{finding.evidence_type.value}] {finding.title}: {finding.summary} "
            f"(confidence: {finding.confidence_note})"
        )
    return "\n".join(lines)


def render_report_json(result: CombinedReport) -> str:
    payload = {
        "target": {
            "raw_target": result.target.raw_target,
            "target_kind": result.target.target_kind.value,
        },
        "limitations": list(result.limitations),
        "findings": [
            {
                "kind": finding.kind,
                "title": finding.title,
                "summary": finding.summary,
                "evidence_type": finding.evidence_type.value,
                "confidence_note": finding.confidence_note,
                "related_modules": list(finding.related_modules),
            }
            for finding in result.findings
        ],
    }
    return json.dumps(payload, indent=2)
