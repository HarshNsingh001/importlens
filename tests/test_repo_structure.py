from __future__ import annotations

from tests.conftest import ROOT_DIR


def test_required_top_level_files_exist() -> None:
    required = {
        "PRODUCT_BRIEF.md",
        "DESIGN_SPEC.md",
        "README.md",
        "pyproject.toml",
    }
    actual = {path.name for path in ROOT_DIR.iterdir() if path.is_file()}
    assert required.issubset(actual)


def test_src_layout_contains_phase_three_packages() -> None:
    src_dir = ROOT_DIR / "src" / "importlens"
    expected = {
        "__init__.py",
        "cli.py",
        "config.py",
        "contract.py",
        "graph.py",
        "models.py",
        "report.py",
        "runtime.py",
        "static.py",
    }
    actual = {path.name for path in src_dir.iterdir() if path.is_file()}
    assert expected == actual


def test_ci_workflow_exists() -> None:
    workflow = ROOT_DIR / ".github" / "workflows" / "ci.yml"
    assert workflow.is_file()

