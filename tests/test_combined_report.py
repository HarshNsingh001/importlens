from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from importlens import cli
from importlens.config import AnalysisConfig
from importlens.report import (
    analyze_report_target,
    build_combined_report,
    derive_report_static_target,
    render_report_json,
    render_report_text,
)
from importlens.runtime import ProfileError, profile_target
from importlens.static import analyze_static_target
from tests.conftest import ROOT_DIR, SNAPSHOTS_DIR


def test_derive_report_static_target_maps_script_target_to_internal_package_scope() -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")
    profile_result = profile_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(internal_only=True),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    derived = derive_report_static_target(profile_result, working_directory=Path.cwd())

    assert derived in {
        "tests\\fixtures\\slow_side_effect\\pkg",
        "tests/fixtures/slow_side_effect/pkg",
    }


def test_analyze_report_target_labels_findings_by_evidence_type_on_one_coherent_target() -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")
    result = analyze_report_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(internal_only=True),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )
    evidence_types = {finding.evidence_type.value for finding in result.findings}

    assert "measured" in evidence_types
    assert "heuristic" in evidence_types or "inferred" in evidence_types


def test_analyze_report_target_produces_actionable_findings_for_one_coherent_target() -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")
    result = analyze_report_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(internal_only=True),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    assert result.findings
    assert any(finding.related_modules for finding in result.findings)


def test_render_report_text_includes_findings_and_limitations() -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")
    result = analyze_report_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(internal_only=True),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    rendered = render_report_text(result)

    assert "findings:" in rendered
    assert "[measured]" in rendered or "[inferred]" in rendered
    assert "limitations:" in rendered


def test_render_report_json_contains_evidence_labels() -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")
    result = analyze_report_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    payload = json.loads(render_report_json(result))

    assert payload["findings"]
    assert all("evidence_type" in finding for finding in payload["findings"])


def test_combined_report_hotspot_uses_deduplicated_static_edges() -> None:
    static_result = analyze_static_target(
        raw_target="tests/fixtures/simple_linear/pkg",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
    )

    result = build_combined_report(profile_result=None, static_result=static_result)

    hotspot_findings = [
        finding for finding in result.findings if finding.kind == "dependency-hotspot"
    ]

    assert hotspot_findings == []


def test_report_deduplicates_repeated_runtime_module_findings() -> None:
    snapshot = "\n".join(
        (
            "import time:         5 |          5 | pkg.entrypoint",
            "import time:         4 |          9 | pkg.entrypoint",
            "import time:         3 |         12 | pkg.slow_module",
        )
    )

    result = analyze_report_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(internal_only=True),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    slow_import_titles = [
        finding.title for finding in result.findings if finding.kind == "slow-import"
    ]

    assert slow_import_titles.count("Slow import: pkg.entrypoint") == 1


def test_report_rejects_package_directory_targets_until_runtime_support_exists() -> None:
    with pytest.raises(ProfileError):
        analyze_report_target(
            raw_target="tests/fixtures/simple_linear/pkg",
            config=AnalysisConfig(),
            working_directory=Path.cwd(),
        )


def test_report_cli_execution_outputs_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "analyze_report_target",
        lambda raw_target, config, working_directory: analyze_report_target(
            raw_target=raw_target,
            config=config,
            working_directory=working_directory,
            runner=lambda _target: snapshot,
        ),
    )

    exit_code = cli.main(["report", "tests/fixtures/slow_side_effect/app.py"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "importlens report" in captured.out
    assert "findings:" in captured.out


def test_report_cli_end_to_end_subprocess() -> None:
    command = [
        sys.executable,
        "-m",
        "importlens.cli",
        "report",
        "tests/fixtures/slow_side_effect/app.py",
        "--internal-only",
    ]

    completed = subprocess.run(
        command,
        cwd=str(ROOT_DIR),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "importlens report" in completed.stdout
    assert "findings:" in completed.stdout
