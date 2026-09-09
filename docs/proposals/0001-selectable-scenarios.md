# 0001 — Selectable scenarios sharing one topology

**Status:** Implemented
**Roadmap item:** "Add selectable scenarios sharing one topology"

## Problem

Today one `::: interactive-flow` directive binds one diagram to one scenario. A
common need is several scenarios over the *same* topology — normal path, failure
path, edge case — switchable in place. The example page already does this by
repeating the directive, which renders the Mermaid diagram twice (the expensive
step) and shows two separate players.

## Goals

- One rendered topology, multiple scenarios, switch without re-rendering Mermaid.
- Switching resets playback to step -1 and keeps the current SVG.
- Each scenario still validated at build; `id`s still unique site-wide
  (already enforced).

## Options — directive shape

- **A. `scenarios:` list** (replaces `scenario:` when plural)
  ```yaml
  ::: interactive-flow
  diagram: flows/cdc.mmd
  scenarios:
    - flows/cdc-normal.yaml
    - flows/cdc-target-offline.yaml
  :::
  ```
  Simple, explicit ordering, backward compatible (`scenario:` still valid).
- **B. glob / directory** — `scenarios: flows/cdc-*.yaml`. Less typing, but
  ordering is implicit and a stray file silently joins the set.
- **C. new directive** `::: interactive-flow-set`. Clean separation but a second
  directive to document and parse.

Implemented as **A**.

## Options — UI

- **Dropdown `<select>`** in the header — compact, scales to many scenarios,
  native keyboard support.
- **Tab row** — one click to switch, but wraps badly past ~4 scenarios / on
  mobile.
- **Segmented buttons** — same wrap problem.

Implemented as a dropdown, using each scenario's `title` as the option label and
an optional directive `title` as the shared group label.

## Behaviour

- `FlowPlayer` swaps `this.scenario`, re-runs the node/edge existence check
  against the already-rendered SVG, resets to -1.
- The `<select>` is part of the `role="group"`; arrow keys still drive playback,
  the select handles its own keys.

## Open questions

1. Group heading: new directive field (`title:`), or derive from the diagram?
2. Deep-linking / restore: `#flow=<id>` in the URL? Remember last choice in
   `localStorage`, or always start on the first?
3. If two scenarios reference nodes the other does not, the existence check runs
   per scenario on switch — acceptable, or pre-check all at build only?
4. Does the counter/aria-live announce the scenario change?
