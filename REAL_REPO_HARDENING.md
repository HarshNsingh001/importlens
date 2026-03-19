# Real-Repo Hardening Assessment

## Purpose

This document records the empirical Phase 7 hardening pass against the pinned validation repositories from the product brief. The goal is to reduce the risk that `importlens` only works on curated fixtures.

## Local Test Baseline

Observed in this workspace with `C:\Users\harsh\OneDrive\Desktop\oster_direc\.venv\Scripts\python.exe`:

- `python -m pytest -q`
  - Observed result: `49 passed in 1.70s`

This means the current blocker is no longer local test execution. The remaining hardening question is how the CLI behaves on real repositories.

## Validation Repositories

### `fastapi/full-stack-fastapi-template`

- Local path: `validation_repos/full-stack-fastapi-template`
- Observed ref: `8bf00250399b18b03247a02518275de626c83238`
- Validation boundary: `backend/app`

Observed commands:

- `importlens graph C:\Users\harsh\OneDrive\Desktop\oster_direc\validation_repos\full-stack-fastapi-template\backend\app`
  - Observed result: success
  - Key output:
    - `node_count: 27`
    - `edge_count: 218`
    - unresolved imports surfaced for external dependencies such as `alembic.context`, `sqlalchemy`, and `sqlmodel.sql.sqltypes`
- `importlens cycles C:\Users\harsh\OneDrive\Desktop\oster_direc\validation_repos\full-stack-fastapi-template\backend\app`
  - Observed result: success
  - Key output:
    - `cycles:`
    - `- no cycles found`
- `importlens profile C:\Users\harsh\OneDrive\Desktop\oster_direc\validation_repos\full-stack-fastapi-template\backend\app\main.py`
  - Observed result: failure
  - Failure detail:
    - `ModuleNotFoundError: No module named 'sentry_sdk'`
- `importlens report C:\Users\harsh\OneDrive\Desktop\oster_direc\validation_repos\full-stack-fastapi-template\backend\app\main.py`
  - Observed result: failure
  - Failure detail:
    - `ModuleNotFoundError: No module named 'sentry_sdk'`
- `importlens profile app.main` from `validation_repos/full-stack-fastapi-template/backend`
  - Observed result: failure
  - Failure detail:
    - `ModuleNotFoundError: No module named 'sentry_sdk'`
- `importlens report app.main` from `validation_repos/full-stack-fastapi-template/backend`
  - Observed result: failure
  - Failure detail:
    - `ModuleNotFoundError: No module named 'sentry_sdk'`

Hardening takeaway:

- Static analysis works cleanly on the backend package and gives a readable summary on a mixed-stack repo when scoped to the Python boundary.
- Runtime-facing commands are currently dependency-sensitive and fail early when the target repo's runtime dependencies are not installed in the active environment.

### `psf/requests`

- Local path: `validation_repos/requests`
- Observed ref: `b25c87d7cb8d6a18a37fa12442b5f883f9e41741`
- Validation boundary: `src/requests`

Observed commands:

- `importlens graph C:\Users\harsh\OneDrive\Desktop\oster_direc\validation_repos\requests\src\requests`
  - Observed result: success
  - Key output:
    - `node_count: 18`
    - `edge_count: 304`
    - summarized output remained readable, with omitted-item messaging present
- `importlens cycles C:\Users\harsh\OneDrive\Desktop\oster_direc\validation_repos\requests\src\requests`
  - Observed result: success
  - Key output:
    - `cycles:`
    - `- no cycles found`
- `importlens profile requests.help` from `validation_repos/requests/src`
  - Observed result: failure
  - Failure detail:
    - `ModuleNotFoundError: No module named 'urllib3'`
- `importlens report requests.help` from `validation_repos/requests/src`
  - Observed result: failure
  - Failure detail:
    - `ModuleNotFoundError: No module named 'urllib3'`

Hardening takeaway:

- Static graph and cycle analysis hold up on a widely used library target.
- Runtime module resolution currently imports enough of the target package to trip external dependency requirements before profiling can start.

### `psf/black`

- Local path: `validation_repos/black`
- Observed ref: `af0ba72a73598c76189d6dd1b21d8532255d5942`
- Validation boundary: `src/black`

Observed commands:

- `importlens graph C:\Users\harsh\OneDrive\Desktop\oster_direc\validation_repos\black\src\black`
  - Observed result: success
  - Key output:
    - `node_count: 25`
    - `edge_count: 497`
    - summarized output remained readable, with omitted-item messaging present
- `importlens cycles C:\Users\harsh\OneDrive\Desktop\oster_direc\validation_repos\black\src\black`
  - Observed result: success
  - Key output:
    - `cycles:`
    - `- no cycles found`
- `importlens profile C:\Users\harsh\OneDrive\Desktop\oster_direc\validation_repos\black\src\black\__main__.py`
  - Observed result: failure
  - Failure detail:
    - `ModuleNotFoundError: No module named 'black'`
- `importlens report C:\Users\harsh\OneDrive\Desktop\oster_direc\validation_repos\black\src\black\__main__.py`
  - Observed result: failure
  - Failure detail:
    - `ModuleNotFoundError: No module named 'black'`
- `importlens profile black.__main__` from `validation_repos/black/src`
  - Observed result: failure
  - Failure detail:
    - `ModuleNotFoundError: No module named 'click'`
- `importlens report black.__main__` from `validation_repos/black/src`
  - Observed result: failure
  - Failure detail:
    - `ModuleNotFoundError: No module named 'click'`

Hardening takeaway:

- Static analysis works on a real CLI package with a dense import graph.
- Script-target profiling is sensitive to import context.
- Module-target profiling is sensitive to target dependencies because local resolvability currently uses `find_spec`, which imports enough package code to trigger dependency failures like missing `click`.

## Scope-Pruning Decisions Confirmed By Hardening

These are now explicit v1 boundaries backed by real-repo outcomes:

- `graph` and `cycles` are the strongest commands today
- `report` remains narrower than `graph` and `cycles`
- package-directory runtime profiling is deferred
- runtime-facing commands require the target environment to have the target's import dependencies available
- whole-repo mixed-language analysis is out of scope
- dynamic and third-party-heavy projects will still produce unresolved imports and explicit caveats

## Current Hardening Outcome

What is empirically hardened:

- the local test suite passes
- `graph` and `cycles` succeed on all three validation repositories
- summarized default text output remains readable on medium and large real-package targets
- unresolved imports are surfaced instead of hidden
- repo-specific runtime/report failures are now observed and understood rather than hypothetical

What remains weaker than desired:

- `profile` and `report` are not yet robust on real repos whose runtime dependencies are not installed in the active environment
- script-target profiling can fail when the script's package root is not on `sys.path`
- module-target resolution can fail early because local resolvability currently depends on import-time behavior

## Conclusion

Phase 7 now has real black-box hardening evidence on the pinned validation repositories. The current v1 candidate is strong for static diagnostics on real package targets, but runtime-facing commands should still be treated as environment-sensitive and not yet broadly hardened across dependency-heavy repos.
