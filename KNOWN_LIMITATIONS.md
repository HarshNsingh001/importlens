# Known Limitations

## Current Command Support

The current v1 candidate supports:

- `profile` for local script targets and locally resolvable module targets
- `graph` for local package directories and Python source paths
- `cycles` for local package directories and Python source paths
- `report` for local script or module targets that allow a coherent internal package scope to be derived

The current v1 candidate does not yet support:

- `report` on package-directory targets
- runtime profiling of package-directory targets
- remote repositories or URLs as direct inputs
- deep dynamic import modeling
- plugin-discovery-heavy architectures
- complete namespace-package semantics

## Trust Boundaries

- Runtime timings are measured, but environment-dependent.
- Static import relationships are inferred and intentionally conservative.
- Unresolved imports are expected in some projects and are reported explicitly.
- Heuristic findings are suggestions, not guaranteed issues.

## Text Output Defaults

- `profile` defaults to a short summary rather than full raw importtime output.
- `graph` defaults to a summarized text view with capped node and edge listings to reduce noise.
- JSON output remains the better choice for complete downstream inspection.

## Validation Gaps

- The local test suite now passes in the workspace environment.
- Real-repo hardening has been run against the pinned repositories.
- The remaining gap is not basic execution evidence. The remaining gap is command maturity:
  - `graph` and `cycles` are more hardened on real repos than `profile` and `report`
  - runtime-facing commands still depend on the target's import environment being available
