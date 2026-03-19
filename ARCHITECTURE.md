# Architecture

`importlens` is intentionally split into small, readable layers so each command can stay honest about what kind of evidence it is producing.

## Layers

- `cli`
  - argument parsing and command dispatch
- `runtime`
  - target resolution for executable targets
  - `-X importtime` invocation
  - import-time parsing and filtering
- `static`
  - AST-based import extraction
  - local module resolution
  - graph and cycle inputs
- `graph`
  - cycle detection
- `report`
  - text and JSON rendering
  - combined findings with evidence labels
- `models`
  - typed shared data structures
- `config`
  - include, exclude, and `internal-only` filters

## Command Flow

### `graph` and `cycles`

1. Resolve a local Python source path or package directory.
2. Collect Python source files inside the target scope.
3. Parse imports with `ast`.
4. Resolve local imports conservatively against the discovered module index.
5. Build edges, unresolved imports, and cycles.
6. Render a summarized text view or full JSON payload.

### `profile`

1. Resolve a script or dotted module target.
2. Execute Python with `-X importtime`.
3. Parse runtime timing lines into structured timing records.
4. Surface parse anomalies instead of silently dropping them.
5. Render a short summary by default or full JSON output.

### `report`

1. Profile a script or module target.
2. Derive one coherent internal package scope from that same target.
3. Run static analysis on the derived internal scope.
4. Merge findings while preserving evidence labels and limitations.

## Trust Model

`importlens` does not treat all outputs as equally certain.

- runtime timings are `measured`
- graph edges and cycles are `inferred`
- hotspot-style guidance is `heuristic`

That distinction is a product feature, not just an implementation detail.

## Why Static Analysis Is Stronger Today

The real-repo hardening pass showed a clear pattern:

- `graph` and `cycles` worked across all three pinned validation repositories
- `profile` and `report` were more sensitive to target import context and missing runtime dependencies

That is why the current public positioning emphasizes static diagnostics first and runtime diagnostics second.
