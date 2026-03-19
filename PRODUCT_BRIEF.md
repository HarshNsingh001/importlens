# importlens Product Brief

## Product Thesis

importlens is a Python library and CLI for developers who need trustworthy diagnostics for Python imports. Its job is to make two common problems easier to understand on real projects: slow startup caused by import-time work, and fragile architecture caused by import cycles or overly connected internal modules. The product should combine measured runtime import timing with approximate but useful static dependency analysis, while being explicit about uncertainty and limitations. The goal is not to act like an automatic optimizer, but to give developers clear evidence they can use to investigate and improve their own codebases.

## Target Users

- Python developers working on medium-sized applications or libraries with noticeable startup or CLI latency
- Maintainers debugging circular imports or tangled internal module relationships
- Developers who want better diagnostics than raw `-X importtime` output without adopting a heavyweight observability tool

## Portfolio Positioning

`importlens` should be positioned as trustworthy diagnostics for Python imports.

It should not be positioned as a fully accurate import optimization advisor or an automatic refactoring tool.

## V1 Scope

### Keep

- `profile`: run runtime import-time profiling for a target script or module
- `graph`: build a static internal import graph for a local package
- `cycles`: detect and report static import cycles
- `report`: combine runtime and static findings into one concise summary
- human-readable text output
- JSON output for tooling and CI use
- include filters
- exclude filters
- internal-only analysis mode

### Explicit Non-Goals

- visual UI or dashboard
- auto-fixes or code rewriting
- IDE/editor integration
- framework-specific hints for Django, FastAPI, or similar ecosystems
- deep support for dynamic import patterns or plugin-loading magic

## Validation Repositories

These are the three concrete validation repositories for Phase 1. They are pinned tightly enough to be reused in later phases.

### 1. Medium Sample Application Repo

- Repository: `fastapi/full-stack-fastapi-template`
- URL: `https://github.com/fastapi/full-stack-fastapi-template`
- Ref for validation: `master` branch, targeting the Python backend only
- Fixture boundary for `importlens`: `backend/`
- Why this target: it is a real application-style repository with a non-trivial Python backend, modern packaging, and enough internal modules to test whether `importlens` stays useful outside a toy library

Repo-specific observations from inspection:

- The repository is structured as a full application template with a dedicated `backend/` directory and a root `pyproject.toml`, which makes it suitable for scoped analysis of the Python backend rather than the whole monorepo.
- The backend sits inside a larger stack with frontend, Docker, and deployment files, which is a good realism test for whether `importlens` can stay disciplined about package boundaries and internal-only output.

Manual assessment:

- Is startup/import behavior confusing today?
  - Yes. Application repositories like this commonly accumulate startup cost across settings, models, API routers, and integration modules, while the real startup path is spread across many files.
- Would timing plus graph output change what I do?
  - Yes. If `importlens` can isolate the backend package graph and correlate it with measured startup cost, it would help prioritize which internal modules deserve cleanup first.
- What output would be actionable versus noise?
  - Actionable: slow internal imports under `backend/`, modules with high internal fan-in or fan-out, exact cycle paths inside the backend package, unresolved imports clearly labeled.
  - Noise: frontend-related files, infrastructure files, or broad recommendations that are not scoped to Python backend imports.

### 2. Moderately Complex Open-Source Library Repo

- Repository: `psf/requests`
- URL: `https://github.com/psf/requests`
- Ref for validation: release `v2.32.5` on the `main` branch lineage
- Fixture boundary for `importlens`: `src/requests/`
- Why this target: it is a widely used, recognizable Python library with a conventional `src/` layout and enough internal modules to test graph quality and output clarity

Repo-specific observations from inspection:

- The repository exposes a clear Python package boundary at `src/requests/` and keeps tests in a separate `tests/` directory, which makes it suitable for internal-only graph analysis.
- Even though the package is well known, the actual internal import structure is not obvious from the outside, which makes it a good check for whether `graph` and `cycles` surface useful structure rather than just trivia.

Manual assessment:

- Is startup/import behavior confusing today?
  - Somewhat. The top-level package is familiar, but the internal import chain and which modules dominate cumulative import cost are not obvious without tooling.
- Would timing plus graph output change what I do?
  - Yes, if the tool can separate first-party package cost from third-party and stdlib cost and show which internal modules are central in the graph.
- What output would be actionable versus noise?
  - Actionable: internal module graph summary, ranking of slowest first-party imports, cycle confirmation, unresolved imports flagged with file context.
  - Noise: restating that third-party dependencies are imported, or generic delay-import advice without package-local evidence.

### 3. CLI Application Repo

- Repository: `psf/black`
- URL: `https://github.com/psf/black`
- Ref for validation: release `26.3.1` on the `main` branch lineage
- Fixture boundary for `importlens`: `src/`
- Why this target: it is a real Python CLI where import-time overhead matters directly to user experience, making it a strong target for `profile` and `report`

Repo-specific observations from inspection:

- The repository has a dedicated `src/` tree plus a `profiling/` directory, which suggests startup and performance are already relevant concerns in the project.
- As a CLI tool, it is a good reality check for whether runtime import diagnostics produce signals that matter to actual command responsiveness.

Manual assessment:

- Is startup/import behavior confusing today?
  - Yes. Users experience CLI startup directly, but the import chain and cumulative startup contribution of internal modules are not obvious from command-line use alone.
- Would timing plus graph output change what I do?
  - Yes. The combination would help distinguish between one-time heavy imports and structural hotspots on the startup path.
- What output would be actionable versus noise?
  - Actionable: cumulative import cost by internal module, top startup-path imports, cycles or heavy internal hubs that affect CLI initialization.
  - Noise: graph detail unrelated to the startup path, or timing output presented with more precision than the environment can justify.

## Usefulness Checks

V1 must pass these checks to justify continuing beyond a technical demo:

1. Internal-signal check:
   - Pass if the default report for each validation repo lists the top 10 slowest internal imports without showing more than 5 stdlib entries in the summary section.
2. Cycle-explanation check:
   - Pass if the tool can show at least one exact cycle path as an ordered module chain on a target that contains a real cycle, or explicitly report that no cycle was found on the pinned target.
3. Evidence-labeling check:
   - Pass if every finding in `report` is tagged as either runtime-measured, statically inferred, or heuristic.
4. Readability check:
   - Pass if the default human-readable summary for a medium target fits within 80 lines of terminal output before optional detail expansion.
5. Actionability check:
   - Pass if each validation target produces at least one finding that identifies a specific internal module or import chain to inspect, rather than only generic statements about startup cost or graph size.

## Demand and Risk Notes

- The biggest product risk is weak demand: import diagnostics may be a real pain point but still not frequent enough to justify a dedicated tool for many developers.
- The biggest implementation risk is trust: if results are noisy, overly broad, or ambiguous without clear labeling, the tool will feel clever rather than reliable.
- The safest reason to build this project is portfolio value plus practical utility, not an assumption of large-scale adoption.

## Validation Decision

Phase 1 should be treated as a conditional go for implementation only if later phases can demonstrate usefulness on the three pinned repositories above. If `importlens` cannot produce trustworthy, scoped, and actionable output on these targets, the project should be narrowed further rather than expanded.
