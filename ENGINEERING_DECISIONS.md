# Engineering Decisions

## 1. Trustworthiness beats feature breadth

The project intentionally favors explicit limits over broad but unreliable behavior. That is why findings are labeled as `measured`, `inferred`, or `heuristic`, and why unresolved imports are surfaced instead of hidden.

## 2. Static diagnostics are the current core

Real-repo hardening showed that `graph` and `cycles` are the most reliable commands today. The project presentation now leads with those capabilities instead of implying that all four commands are equally mature.

## 3. Runtime failures should be honest

If a target cannot import because its environment is incomplete, `profile` and `report` fail with the actual runtime error. V1 does not try to mask those failures behind partial or fabricated output.

## 4. Summaries by default, full data in JSON

Text output is intentionally capped so real-package runs stay readable in a terminal. JSON remains the escape hatch for complete downstream inspection.

## 5. Combined reports must stay coherent

The `report` command only combines runtime and static analysis when both halves can be tied to one coherent target. This avoids a stitched output that looks polished but mixes unrelated scopes.

## 6. Narrow scope is part of the portfolio story

This project is meant to show disciplined engineering:

- a clear product thesis
- typed models and tests
- conservative analysis behavior
- empirical hardening on real repositories

The project is stronger as a focused, honest tool than it would be as a broader but less trustworthy one.
