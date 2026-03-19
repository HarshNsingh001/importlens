from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from importlens import cli
from importlens.config import AnalysisConfig
from importlens.models import ImportEdge, ImportLocation
from importlens.report import (
    render_cycles_text,
    render_graph_json,
)
from importlens.static import (
    ModuleSource,
    analyze_static_target,
    deduplicate_import_edges,
    relative_import_context,
    resolve_static_import,
    resolve_static_target,
)
from tests.conftest import ROOT_DIR, SNAPSHOTS_DIR


def test_resolve_static_target_supports_package_directories() -> None:
    target = resolve_static_target("tests/fixtures/simple_linear/pkg", working_directory=Path.cwd())

    assert target.target_kind.value == "package"
    assert target.resolved_path is not None
    assert target.resolved_path.name == "pkg"


def test_analyze_static_target_matches_simple_linear_snapshot() -> None:
    expected = json.loads(
        (SNAPSHOTS_DIR / "simple_linear_graph.json").read_text(encoding="utf-8")
    )

    result = analyze_static_target(
        raw_target="tests/fixtures/simple_linear/pkg",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
    )

    nodes = [
        node.module_name
        for node in sorted(result.module_nodes, key=lambda item: item.module_name)
    ]
    edges = [
        [edge.importer, edge.imported]
        for edge in sorted(result.import_edges, key=lambda item: (item.importer, item.imported))
        if edge.is_resolved
    ]

    assert nodes == expected["nodes"]
    assert edges == expected["edges"]


def test_analyze_static_target_matches_relative_import_snapshot() -> None:
    expected = json.loads(
        (SNAPSHOTS_DIR / "relative_imports_graph.json").read_text(encoding="utf-8")
    )

    result = analyze_static_target(
        raw_target="tests/fixtures/relative_imports/pkg",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
    )

    nodes = [
        node.module_name
        for node in sorted(result.module_nodes, key=lambda item: item.module_name)
    ]
    edges = [
        [edge.importer, edge.imported]
        for edge in sorted(result.import_edges, key=lambda item: (item.importer, item.imported))
        if edge.is_resolved
    ]

    assert nodes == expected["nodes"]
    assert edges == expected["edges"]


def test_relative_import_context_keeps_package_scope_for_init_modules() -> None:
    assert relative_import_context("pkg.subpkg.__init__") == "pkg.subpkg"
    assert relative_import_context("pkg.service") == "pkg"


def test_relative_symbol_resolution_preserves_qualified_package_prefix() -> None:
    resolved = resolve_static_import(
        imported="subpkg.helpers.helper_value",
        current_package="pkg",
        level=1,
        module_index={
            "pkg.subpkg.helpers": ModuleSource(
                module_name="pkg.subpkg.helpers",
                file_path=(
                    ROOT_DIR
                    / "tests"
                    / "fixtures"
                    / "relative_imports"
                    / "pkg"
                    / "subpkg"
                    / "helpers.py"
                ),
            )
        },
    )

    assert resolved == "pkg.subpkg.helpers"


def test_analyze_static_target_reports_unresolved_dynamic_imports() -> None:
    result = analyze_static_target(
        raw_target="tests/fixtures/optional_dynamic/pkg",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
    )

    unresolved_names = {(edge.importer, edge.imported) for edge in result.unresolved_imports}

    assert ("pkg.loader", "importlib") in unresolved_names
    assert result.limitations


def test_analyze_static_target_detects_circular_chain() -> None:
    expected = json.loads(
        (SNAPSHOTS_DIR / "circular_chain_cycles.json").read_text(encoding="utf-8")
    )

    result = analyze_static_target(
        raw_target="tests/fixtures/circular_chain/pkg",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
    )

    cycles = [list(cycle.modules) for cycle in result.cycles]

    assert cycles == expected["cycles"]


def test_deduplicate_import_edges_collapses_repeated_same_site_edges() -> None:
    file_path = ROOT_DIR / "tests" / "fixtures" / "simple_linear" / "pkg" / "__init__.py"
    duplicated = (
        ImportEdge(
            importer="pkg.__init__",
            imported="pkg.alpha",
            import_kind="from",
            location=ImportLocation(file_path=file_path, line_number=1),
            is_resolved=True,
        ),
        ImportEdge(
            importer="pkg.__init__",
            imported="pkg.alpha",
            import_kind="from",
            location=ImportLocation(file_path=file_path, line_number=1),
            is_resolved=True,
        ),
        ImportEdge(
            importer="pkg.__init__",
            imported="pkg.alpha",
            import_kind="from",
            location=ImportLocation(file_path=file_path, line_number=2),
            is_resolved=True,
        ),
    )

    result = deduplicate_import_edges(duplicated)

    assert len(result) == 2
    assert result[0].location.line_number == 1
    assert result[1].location.line_number == 2


def test_render_graph_json_includes_unresolved_imports() -> None:
    result = analyze_static_target(
        raw_target="tests/fixtures/optional_dynamic/pkg",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
    )

    payload = json.loads(render_graph_json(result))

    assert payload["unresolved_imports"]
    assert payload["limitations"]


def test_render_cycles_text_reports_no_cycles_when_none_found() -> None:
    result = analyze_static_target(
        raw_target="tests/fixtures/simple_linear/pkg",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
    )

    rendered = render_cycles_text(result)

    assert "no cycles found" in rendered


def test_graph_cli_execution_outputs_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = analyze_static_target(
        raw_target="tests/fixtures/simple_linear/pkg",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
    )
    monkeypatch.setattr(
        cli,
        "analyze_static_target",
        lambda raw_target, config, working_directory: result,
    )

    exit_code = cli.main(["graph", "tests/fixtures/simple_linear/pkg"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "importlens graph" in captured.out
    assert "pkg.alpha -> pkg.beta" in captured.out


def test_cycles_cli_execution_outputs_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = analyze_static_target(
        raw_target="tests/fixtures/circular_chain/pkg",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
    )
    monkeypatch.setattr(
        cli,
        "analyze_static_target",
        lambda raw_target, config, working_directory: result,
    )

    exit_code = cli.main(["cycles", "tests/fixtures/circular_chain/pkg"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "importlens cycles" in captured.out
    assert "pkg.a -> pkg.b -> pkg.c -> pkg.a" in captured.out


def test_graph_cli_end_to_end_subprocess() -> None:
    command = [
        sys.executable,
        "-m",
        "importlens.cli",
        "graph",
        "tests/fixtures/simple_linear/pkg",
    ]

    completed = subprocess.run(
        command,
        cwd=str(ROOT_DIR),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "importlens graph" in completed.stdout
    assert "pkg.alpha -> pkg.beta" in completed.stdout


def test_cycles_cli_end_to_end_subprocess() -> None:
    command = [
        sys.executable,
        "-m",
        "importlens.cli",
        "cycles",
        "tests/fixtures/circular_chain/pkg",
    ]

    completed = subprocess.run(
        command,
        cwd=str(ROOT_DIR),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "importlens cycles" in completed.stdout
    assert "pkg.a -> pkg.b -> pkg.c -> pkg.a" in completed.stdout
