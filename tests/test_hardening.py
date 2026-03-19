from __future__ import annotations

from pathlib import Path

from importlens.models import (
    EvidenceType,
    ImportEdge,
    ImportLocation,
    ModuleNode,
    StaticAnalysisResult,
    TargetKind,
    TargetSpec,
)
from importlens.report import render_graph_text


def test_graph_text_output_is_summarized_for_noisy_targets() -> None:
    target = TargetSpec(
        raw_target="synthetic/pkg",
        target_kind=TargetKind.PACKAGE,
        resolved_path=Path("synthetic/pkg"),
        package_root=Path("synthetic"),
        internal_prefixes=("pkg",),
    )
    nodes = tuple(
        ModuleNode(
            module_name=f"pkg.module_{index:02d}",
            file_path=Path(f"synthetic/pkg/module_{index:02d}.py"),
            is_internal=True,
            is_resolved=True,
        )
        for index in range(20)
    )
    edges = tuple(
        ImportEdge(
            importer=f"pkg.module_{index:02d}",
            imported=f"pkg.module_{index + 1:02d}",
            import_kind="import",
            location=ImportLocation(Path(f"synthetic/pkg/module_{index:02d}.py"), index + 1),
            is_resolved=True,
            source=EvidenceType.INFERRED,
        )
        for index in range(19)
    )
    result = StaticAnalysisResult(
        target=target,
        module_nodes=nodes,
        import_edges=edges,
        cycles=(),
        limitations=(),
        unresolved_imports=(),
    )

    rendered = render_graph_text(result)

    assert "node_count:" in rendered
    assert "edge_count:" in rendered
    assert "more nodes omitted from text output" in rendered
    assert "more edges omitted from text output" in rendered
    assert "pkg.module_00" in rendered
    assert "pkg.module_19" not in rendered


def test_known_limitations_documents_report_target_boundary() -> None:
    contents = Path("KNOWN_LIMITATIONS.md").read_text(encoding="utf-8")

    assert "`report` on package-directory targets" in contents
