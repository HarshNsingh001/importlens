from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from importlens.config import AnalysisConfig
from importlens.models import TargetKind
from importlens.report import render_profile_json, render_profile_text
from importlens.runtime import (
    ProfileError,
    parse_importtime_output,
    profile_target,
    resolve_target,
)
from tests.conftest import ROOT_DIR, SNAPSHOTS_DIR


def test_parse_importtime_output_matches_snapshot_order_and_values() -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")

    records, anomalies = parse_importtime_output(snapshot)

    assert [record.module_name for record in records] == [
        "pkg.slow_module",
        "pkg.entrypoint",
        "pkg",
    ]
    assert [record.cumulative_time_us for record in records] == [12, 16, 19]
    assert all(record.source.value == "measured" for record in records)
    assert anomalies == ()


def test_parse_importtime_output_reports_anomalies_instead_of_silently_skipping() -> None:
    output = "\n".join(
        (
            "import time:         1 |          1 | pkg.alpha",
            "not a valid importtime line",
        )
    )

    records, anomalies = parse_importtime_output(output)

    assert [record.module_name for record in records] == ["pkg.alpha"]
    assert len(anomalies) == 1
    assert anomalies[0].line_number == 2


def test_parse_importtime_output_ignores_standard_cpython_header() -> None:
    output = "\n".join(
        (
            "import time: self [us] | cumulative | imported package",
            "import time:         1 |          1 | pkg.alpha",
        )
    )

    records, anomalies = parse_importtime_output(output)

    assert [record.module_name for record in records] == ["pkg.alpha"]
    assert anomalies == ()


def test_resolve_target_supports_python_script_paths() -> None:
    target = resolve_target("tests/fixtures/slow_side_effect/app.py", working_directory=Path.cwd())

    assert target.target_kind is TargetKind.SCRIPT
    assert target.resolved_path is not None
    assert target.resolved_path.name == "app.py"
    assert "pkg" in target.internal_prefixes


def test_resolve_target_rejects_urls() -> None:
    with pytest.raises(ProfileError, match="URLs are not accepted"):
        resolve_target("https://example.com/repo.py", working_directory=Path.cwd())


def test_resolve_target_supports_locally_resolvable_module_targets() -> None:
    fixture_root = ROOT_DIR / "tests" / "fixtures" / "slow_side_effect"

    target = resolve_target("pkg.entrypoint", working_directory=fixture_root)

    assert target.target_kind is TargetKind.MODULE
    assert target.resolved_path is not None
    assert target.resolved_path.name == "entrypoint.py"
    assert target.internal_prefixes == ("pkg",)


def test_profile_target_filters_to_internal_modules() -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")

    result = profile_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(internal_only=True),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    assert [record.module_name for record in result.timing_records] == [
        "pkg",
        "pkg.entrypoint",
        "pkg.slow_module",
    ]
    assert result.limitations


def test_profile_target_supports_module_targets_with_runner() -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")
    fixture_root = ROOT_DIR / "tests" / "fixtures" / "slow_side_effect"

    result = profile_target(
        raw_target="pkg.entrypoint",
        config=AnalysisConfig(internal_only=True),
        working_directory=fixture_root,
        runner=lambda _target: snapshot,
    )

    assert result.target.target_kind is TargetKind.MODULE
    assert result.timing_records[0].module_name == "pkg"


def test_profile_target_honors_include_and_exclude_filters() -> None:
    snapshot = "\n".join(
        (
            "import time:         1 |          1 | pkg.alpha",
            "import time:         2 |          3 | pkg.beta",
            "import time:         3 |          6 | external.lib",
        )
    )

    result = profile_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(include=("pkg",), exclude=("beta",), internal_only=False),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    assert [record.module_name for record in result.timing_records] == ["pkg.alpha"]


def test_render_profile_text_includes_limitations_and_measured_evidence() -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")
    result = profile_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    rendered = render_profile_text(result)

    assert "limitations:" in rendered
    assert "evidence=measured" in rendered
    assert "pkg.slow_module" in rendered


def test_render_profile_text_summarizes_records_instead_of_dumping_everything() -> None:
    snapshot = "\n".join(
        [
            f"import time:         1 |        {index:>3} | importlib.module_{index}"
            for index in range(1, 15)
        ]
    )
    result = profile_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    rendered = render_profile_text(result)

    assert "summary_records:" in rendered
    assert rendered.count("evidence=measured") == 10
    assert "importlib.module_4" not in rendered


def test_render_profile_text_deduplicates_summary_modules() -> None:
    snapshot = "\n".join(
        (
            "import time:         5 |          5 | pkg.entrypoint",
            "import time:         4 |          9 | pkg.entrypoint",
            "import time:         3 |         12 | pkg.slow_module",
        )
    )
    result = profile_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(internal_only=True),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    rendered = render_profile_text(result)

    assert rendered.count("pkg.entrypoint:") == 1


def test_render_profile_text_surfaces_parse_anomalies() -> None:
    snapshot = "\n".join(
        (
            "import time:         1 |          1 | pkg.alpha",
            "malformed line",
        )
    )
    result = profile_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    rendered = render_profile_text(result)

    assert "parse_anomalies:" in rendered
    assert "malformed line" in rendered


def test_render_profile_json_contains_expected_payload_shape() -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")
    result = profile_target(
        raw_target="tests/fixtures/slow_side_effect/app.py",
        config=AnalysisConfig(),
        working_directory=Path.cwd(),
        runner=lambda _target: snapshot,
    )

    payload = json.loads(render_profile_json(result))

    assert payload["target"]["raw_target"] == "tests/fixtures/slow_side_effect/app.py"
    assert payload["timing_records"][0]["source"] == "measured"
    assert "summary_records" in payload
    assert payload["limitations"]


def test_profile_target_rejects_package_directory_execution_for_now() -> None:
    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")

    with pytest.raises(ProfileError, match="not executable"):
        profile_target(
            raw_target="tests/fixtures/simple_linear/pkg",
            config=AnalysisConfig(),
            working_directory=Path.cwd(),
            runner=lambda _target: snapshot,
        )


def test_cli_profile_execution_outputs_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from importlens import cli

    snapshot = (SNAPSHOTS_DIR / "slow_side_effect_importtime.txt").read_text(encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "profile_target",
        lambda raw_target, config, working_directory: profile_target(
            raw_target=raw_target,
            config=config,
            working_directory=working_directory,
            runner=lambda _target: snapshot,
        ),
    )

    exit_code = cli.main(["profile", "tests/fixtures/slow_side_effect/app.py"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "importlens profile" in captured.out
    assert "pkg.slow_module" in captured.out


def test_cli_profile_end_to_end_subprocess() -> None:
    command = [
        sys.executable,
        "-m",
        "importlens.cli",
        "profile",
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
    assert "importlens profile" in completed.stdout
    assert "pkg.slow_module" in completed.stdout
