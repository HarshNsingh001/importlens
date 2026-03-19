# Phase 7 Hardening Note

## What Was Hardened

- Default text output for `graph` is now summarized to reduce noise on medium-sized targets.
- The repository now includes an explicit known-limitations document so unsupported cases are easier to understand before use.
- The current target-support boundaries are documented plainly instead of being implied.
- A real-repo hardening assessment has been executed against the pinned validation targets.
- The local test suite now passes in the workspace environment.

## Scope Pruning Decisions

The following remain intentionally deferred or pruned for this v1 candidate:

- package-directory support for `report`
- deeper runtime/static cross-correlation
- auto-fix suggestions
- visualization/dashboard output
- framework-specific analysis

## Why This Matters

Phase 7 is about making the current candidate safer and clearer, not broader.

The current implementation is strongest when treated as:

- a narrow diagnostics CLI
- with explicit trust boundaries
- summarized default output
- and documented unsupported cases

## Remaining Hardening Risk

The main risk is no longer missing execution evidence. The main remaining risk is uneven real-repo strength across commands:

- `graph` and `cycles` behaved well on all three validation repositories
- `profile` and `report` still fail on real repos when the active environment lacks the target project's runtime dependencies
- module-target resolvability is still more import-sensitive than ideal on third-party packages

This means the Phase 7 candidate is now empirically hardened for static diagnostics on real repos, but only partially hardened for runtime-facing commands.
