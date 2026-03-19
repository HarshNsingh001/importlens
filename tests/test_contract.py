from __future__ import annotations

from importlens.contract import CLI_TARGET_FORMS, CLI_UNSUPPORTED_TARGETS


def test_cli_contract_locks_down_three_target_forms() -> None:
    assert tuple(form.name for form in CLI_TARGET_FORMS) == (
        "script-path",
        "package-directory",
        "module-name",
    )


def test_each_target_form_declares_examples_and_failure_modes() -> None:
    for form in CLI_TARGET_FORMS:
        assert form.accepted_examples
        assert form.failure_modes


def test_cli_contract_rejects_unsupported_targets() -> None:
    assert "urls" in CLI_UNSUPPORTED_TARGETS
    assert "missing paths" in CLI_UNSUPPORTED_TARGETS
    assert "non-python files" in CLI_UNSUPPORTED_TARGETS

