from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetForm:
    name: str
    description: str
    accepted_examples: tuple[str, ...]
    failure_modes: tuple[str, ...]


CLI_TARGET_FORMS: tuple[TargetForm, ...] = (
    TargetForm(
        name="script-path",
        description="Local Python script path.",
        accepted_examples=("app.py", "tools/runner.py"),
        failure_modes=("missing-path", "non-python-file", "url-input"),
    ),
    TargetForm(
        name="package-directory",
        description="Local package directory containing Python modules.",
        accepted_examples=("src/my_package", "backend/app"),
        failure_modes=("missing-path", "not-a-directory", "url-input"),
    ),
    TargetForm(
        name="module-name",
        description="Resolvable local module target.",
        accepted_examples=("pkg.module", "app.main"),
        failure_modes=("unresolvable-module", "ambiguous-module", "url-input"),
    ),
)

CLI_UNSUPPORTED_TARGETS: tuple[str, ...] = (
    "remote repositories",
    "urls",
    "non-local execution targets",
    "missing paths",
    "non-python files",
)

