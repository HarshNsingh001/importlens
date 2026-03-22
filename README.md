# importlens

`importlens` is a Python library and CLI for trustworthy diagnostics of Python imports.

The current v1 candidate is built to help developers inspect import-time cost, internal import structure, and circular dependencies without overstating certainty or acting like an automatic optimizer.

## Problem

Python import issues are easy to feel and hard to inspect.

- CLI tools can feel slow without a clear picture of which imports dominate startup.
- Applications can accumulate tangled internal modules that make import cycles and fragile package structure harder to reason about.
- Raw profiling output exists, but it is hard to connect to package architecture and harder to trust without clear labeling.

`importlens` aims to combine measured runtime timing with approximate static graph analysis in a way that stays honest about what is known, what is inferred, and what remains uncertain.

## Scope

V1 is intentionally small.

- `profile`: runtime import-time diagnostics for a local target
- `graph`: static import graph analysis for a local package or path
- `cycles`: cycle detection from the inferred static graph
- `report`: a combined human-readable or JSON summary

V1 will not include dashboards, IDE integration, auto-fixes, or deep support for dynamic import systems.

## Current Status

Observed in this workspace:

- the current test suite passes locally (`49 passed` on the latest rerun)
- real-repo hardening runs completed against the pinned validation repositories
- `graph` and `cycles` are currently the strongest commands on real package targets
- `profile` and `report` remain more environment-sensitive on dependency-heavy repos

This means `importlens` is already credible as a static diagnostics tool, while the runtime-facing commands should still be treated as narrower and more environment-sensitive.

## Installation

For standard use:

```bash
pip install importlens
```

For development and local testing:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

## Commands

```bash
importlens graph src/my_package
importlens cycles src/my_package
importlens profile app.py
importlens report app.py
```

Accepted target forms:

- local script paths such as `app.py`
- local package directories such as `src/my_package`
- local module targets such as `pkg.module` when they can be resolved locally

## Example Output

Static graph analysis on a real package target:

```text
importlens graph
target: ...\validation_repos\requests\src\requests
target_type: package
node_count: 18
edge_count: 304
limitations:
- Some imports could not be resolved statically and are reported as unresolved.
```

Cycle detection on the same target:

```text
importlens cycles
target: ...\validation_repos\requests\src\requests
target_type: package
cycles:
- no cycles found
```

Runtime profiling on dependency-heavy repos currently fails honestly when the active environment cannot import the target:

```text
error: Runtime profiling failed: ...
ModuleNotFoundError: No module named 'urllib3'
```

That failure mode is intentional product behavior for v1: `importlens` does not pretend a runtime profile succeeded when the target cannot actually import.

## Validation

The repository includes:

- a product brief in [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md)
- a design specification in [DESIGN_SPEC.md](DESIGN_SPEC.md)
- fixture packages under `tests/fixtures/`
- command, analysis, and report tests under `tests/`
- a real-repo hardening report in [REAL_REPO_HARDENING.md](REAL_REPO_HARDENING.md)
- hardening notes in [PHASE7_HARDENING_NOTE.md](PHASE7_HARDENING_NOTE.md)
- explicit support boundaries in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)
- an architecture walkthrough in [ARCHITECTURE.md](ARCHITECTURE.md)
- an engineering decisions note in [ENGINEERING_DECISIONS.md](ENGINEERING_DECISIONS.md)

## CLI Target Forms

Accepted target forms for v1 are locked down early so command behavior stays testable:

- local script path, for example `app.py`
- local package directory, for example `src/my_package`
- local module target when it can be resolved reliably, for example `pkg.module`

The CLI should reject:

- URLs
- non-Python files
- missing paths
- ambiguous targets that cannot be resolved cleanly

## Known Limitations

- Runtime timing is environment-dependent and should not be treated as a stable benchmark.
- Static graph analysis is approximate and will not fully model dynamic imports or plugin loading.
- Runtime-facing commands currently depend on the target's import environment being available.
- `report` currently supports script and module targets only; package-directory report support is intentionally deferred until runtime profiling support catches up.

For the current support matrix and empirical hardening results, see [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) and [REAL_REPO_HARDENING.md](REAL_REPO_HARDENING.md).

## License

`importlens` is licensed under the MIT License. See [LICENSE](LICENSE) for details.
