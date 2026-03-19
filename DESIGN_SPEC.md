# importlens Design Spec

## Purpose

This document defines the Phase 2 design for `importlens`. The design is intentionally narrow and trust-oriented. `importlens` should help developers inspect Python import behavior without overstating certainty, promising automatic optimization, or pretending to model every import edge case in Python.

## Design Goals

- produce diagnostics that are understandable and scoped to real developer decisions
- distinguish clearly between measured behavior and inferred structure
- keep v1 small enough to implement and validate on real repositories
- optimize for trustworthiness and clarity over cleverness
- build a codebase that is production-grade and easy to extend without widening scope prematurely

## Trust Model

`importlens` must present every result according to its source and confidence.

### Runtime Timing

- Runtime timing is measured data collected from Python's import profiling behavior.
- Measured timing is useful, but environment-dependent.
- Runtime results may vary based on machine speed, cache state, installed dependencies, Python version, and target entrypoint.
- Runtime timing should never be framed as a stable benchmark.

### Static Graph Analysis

- Static graph analysis is inferred from source code.
- Static results are approximate but useful for understanding internal structure.
- Static analysis may miss dynamic imports, plugin loading, generated modules, or imports hidden behind runtime conditions.
- Static graph results should help explain architecture, not claim full import-semantic completeness.

### Guidance and Suggestions

- Guidance should be conservative and traceable to evidence.
- Suggestions must be labeled so the user can tell whether they come from measured runtime data, static inference, or a heuristic rule.
- `importlens` should not claim guaranteed performance gains or guaranteed correctness of suggested changes.

## Output Principles

Every user-facing report must follow these rules:

1. Every finding is tagged as one of:
   - `measured`
   - `inferred`
   - `heuristic`
2. Ambiguous or partial results are stated explicitly.
3. Unresolved imports are reported as unresolved instead of being silently dropped.
4. Findings should prioritize internal modules over stdlib and third-party noise when `internal-only` mode is active.
5. Default output should summarize before expanding into detail.
6. No output should imply a recommendation is guaranteed to improve performance or fix correctness issues.

## V1 Package Structure

The codebase should use a `src` layout and the following package structure:

- `importlens.cli`
  - command entrypoints
  - argument parsing
  - command dispatch
- `importlens.runtime`
  - subprocess execution for runtime import profiling
  - parsing and normalization of import timing data
- `importlens.static`
  - source discovery
  - AST parsing
  - import extraction
  - relative import resolution
- `importlens.graph`
  - graph construction
  - cycle detection
  - dependency metrics
- `importlens.report`
  - text rendering
  - JSON serialization
  - report assembly
- `importlens.models`
  - shared typed domain models
- `importlens.config`
  - include and exclude filters
  - internal-only analysis rules
  - path and package root configuration

## Core Models

These models should exist in v1.

### `TargetSpec`

Represents a user target for analysis.

Fields:

- `raw_target`: original user input
- `target_type`: script, module, or package path
- `resolved_path`: normalized local path when applicable
- `package_root`: inferred package root for static analysis

### `TimingRecord`

Represents one runtime import timing record.

Fields:

- `module_name`
- `self_time_us`
- `cumulative_time_us`
- `import_depth`
- `source`: always `measured`

### `ModuleNode`

Represents one internal module in the static graph.

Fields:

- `module_name`
- `file_path`
- `is_internal`
- `is_resolved`

### `ImportEdge`

Represents one directed import relationship.

Fields:

- `importer`
- `imported`
- `import_kind`
- `location`
- `is_resolved`
- `source`: always `inferred`

### `CycleFinding`

Represents one detected cycle.

Fields:

- `modules`
- `edge_locations`
- `source`: always `inferred`

### `Finding`

Represents one user-facing report item.

Fields:

- `kind`
- `title`
- `summary`
- `evidence_type`
- `confidence_note`
- `related_modules`

### `AnalysisReport`

Represents the combined result of one command or merged report.

Fields:

- `target`
- `timing_records`
- `module_nodes`
- `import_edges`
- `cycles`
- `findings`
- `limitations`

## CLI Contract

The CLI should remain minimal in v1.

### `importlens profile <target>`

Purpose:

- run runtime import profiling on a local Python script or module target
- return timing-focused diagnostics

Core options:

- `--format text|json`
- `--include <pattern>`
- `--exclude <pattern>`
- `--internal-only`

### `importlens graph <target>`

Purpose:

- build and display a static internal import graph for a local package or path

Core options:

- `--format text|json`
- `--include <pattern>`
- `--exclude <pattern>`
- `--internal-only`

### `importlens cycles <target>`

Purpose:

- detect and report static import cycles for a local package or path

Core options:

- `--format text|json`
- `--include <pattern>`
- `--exclude <pattern>`
- `--internal-only`

### `importlens report <target>`

Purpose:

- combine runtime timing and static graph findings into one scoped report

Core options:

- `--format text|json`
- `--include <pattern>`
- `--exclude <pattern>`
- `--internal-only`

## Target Input Constraints

V1 should explicitly support only the following:

- local script paths
- local package directories
- local module execution targets when they can be resolved reliably

V1 should explicitly not promise full support for:

- remote repositories or URLs as direct inputs
- non-local execution environments
- complex plugin discovery systems
- generated modules
- arbitrary dynamic import behavior
- every namespace-package edge case

The tool should fail clearly when input is unsupported or ambiguous.

## Command Acceptance Criteria

### `profile`

`profile` is acceptable for v1 if it can:

- execute a local target under runtime import profiling
- parse the timing output into structured records
- filter output with include and exclude patterns
- prefer internal module summaries when `--internal-only` is active
- render both text and JSON output
- include a limitations note explaining that runtime timing is environment-dependent

`profile` is not acceptable if it:

- presents timing as stable benchmarking data
- silently drops parsing failures
- floods the summary with irrelevant stdlib noise by default

### `graph`

`graph` is acceptable for v1 if it can:

- discover Python source files within a target boundary
- extract static imports using AST parsing
- resolve common local imports for standard package layouts
- mark unresolved imports explicitly
- render internal module relationships in text and JSON output

`graph` is not acceptable if it:

- pretends unresolved imports are resolved
- implies the graph is complete in the presence of unsupported dynamic behavior

### `cycles`

`cycles` is acceptable for v1 if it can:

- detect static cycles from the inferred graph
- output exact ordered module chains for each cycle found
- report when no cycles are found in the analyzed scope
- include enough module or file context for a developer to follow the cycle path

`cycles` is not acceptable if it:

- returns only a generic "cycle exists" message without a traceable chain
- hides uncertainty about partial graph coverage

### `report`

`report` is acceptable for v1 if it can:

- merge runtime and static results into one concise summary
- tag every finding as measured, inferred, or heuristic
- surface limitations and unresolved cases clearly
- produce at least one actionable, specific finding per useful target when evidence exists
- keep the default text output within the readability limit defined in the product brief

`report` is not acceptable if it:

- mixes evidence types without labels
- offers aggressive optimization advice unsupported by the analysis
- produces a stitched output that feels like unrelated command dumps

## Error-Handling Principles

- prefer explicit failures over silent fallback when input cannot be understood
- preserve partial results when safe, but label them as partial
- distinguish user errors, unsupported targets, and internal parsing failures
- keep error messages concrete and tied to the target or file that caused the issue

## Non-Goals for the Design

This design intentionally excludes:

- automatic refactoring
- editor integration
- visualization UI
- framework-specific tuning logic
- advanced benchmark features
- deep import-hook instrumentation beyond the runtime profiling source

## Phase 2 Exit Criteria

Phase 2 is complete when the project has:

- a documented trust model
- output principles that govern every command
- a stable v1 package structure
- defined core domain models
- a minimal CLI contract
- explicit input constraints
- command-level acceptance criteria

## Carry-Forward Note

Before fixture-based validation begins, the validation repository references in the product brief should be converted from branch-lineage descriptions to immutable tags or commit SHAs where possible.
