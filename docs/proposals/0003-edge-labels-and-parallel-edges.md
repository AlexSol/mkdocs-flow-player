# 0003 — Edge labels and parallel edges

**Status:** Implemented
**Roadmap item:** "Support Mermaid edge labels and multiple edges between the same
nodes robustly"

## Problem

Two limitations:

1. `parse_topology` rejects a second edge between the same ordered pair
   ("Parallel edge `A->B` is ambiguous"), because a scenario step's
   `edge: { from, to }` cannot say *which* one. Real diagrams have retry /
   bidirectional / alternate-path edges.
2. Edge label text (`A -->|WAL| B`) is parsed and discarded; the scenario can't
   reference it or show it in the details panel.

## Options — disambiguating an edge in the DSL

- **A. ordinal** — `edge: { from: A, to: B, nth: 2 }` (1-based, source order).
  Mermaid already names parallel edge paths `L_A_B_0`, `L_A_B_1`, … in source
  order, so `nth` maps straight onto the path id suffix — cheap in JS.
- **B. label** — `edge: { from: A, to: B, label: "retry" }`, matching the
  Mermaid `|label|`. Reads well; needs labels to be unique among A→B edges.
- **C. Mermaid edge IDs** — `A e1@--> B` (new Mermaid syntax). Cleanest source
  side but currently rejected by the parser and ties us to a newer Mermaid.

Implemented as **A + B**: accept either `nth` or `label`; `{from, to}` alone stays valid
when there is exactly one A→B edge (backward compatible).

## Parser / validator changes

- `Topology.edges` becomes an ordered list of records
  `{from, to, label, index}` instead of a set of pairs.
- `validate_scenario` matches an edge step by `(from, to)` plus `nth`/`label`
  when given; errors listing the candidates when ambiguous.
- Edge label exposed to the renderer so `travel` steps can show it.

## JS

- `findEdge(from, to, nth)` selects `L_<from>_<to>_<nth-1>` (the trailing
  counter already disambiguates).

## Open questions

1. Ambiguous with no disambiguator: keep the hard build error (current), or pick
   the first and warn?
2. If both `nth` and `label` are given and disagree — error, or `nth` wins?
3. Does the traveller step render the edge label automatically, or only when the
   step has no `title`?
4. Self-loops (`A --> A`) — in scope here or a separate item?
