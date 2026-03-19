from __future__ import annotations

import json

from tests.conftest import FIXTURES_DIR, SNAPSHOTS_DIR

EXPECTED_FIXTURES = {
    "simple_linear",
    "circular_chain",
    "relative_imports",
    "optional_dynamic",
    "slow_side_effect",
}


def test_expected_fixture_projects_exist() -> None:
    actual = {path.name for path in FIXTURES_DIR.iterdir() if path.is_dir()}
    assert EXPECTED_FIXTURES.issubset(actual)


def test_fixture_projects_include_python_sources() -> None:
    for fixture_name in EXPECTED_FIXTURES:
        fixture_dir = FIXTURES_DIR / fixture_name
        assert any(fixture_dir.rglob("*.py")), fixture_name


def test_snapshots_exist_for_graph_cycle_and_runtime_expectations() -> None:
    expected_files = {
        "simple_linear_graph.json",
        "circular_chain_cycles.json",
        "relative_imports_graph.json",
        "optional_dynamic_graph.json",
        "slow_side_effect_importtime.txt",
    }
    actual_files = {path.name for path in SNAPSHOTS_DIR.iterdir() if path.is_file()}
    assert expected_files == actual_files


def test_json_snapshots_are_valid() -> None:
    for snapshot in SNAPSHOTS_DIR.glob("*.json"):
        data = json.loads(snapshot.read_text(encoding="utf-8"))
        assert isinstance(data, dict)


def test_text_snapshot_has_expected_importtime_shape() -> None:
    snapshot = SNAPSHOTS_DIR / "slow_side_effect_importtime.txt"
    lines = snapshot.read_text(encoding="utf-8").splitlines()
    assert lines
    assert any("import time:" in line for line in lines)

