# 0002 — Node metadata and documentation links

**Status:** Draft — needs decision
**Roadmap item:** "Add node metadata/details and documentation links"

## Problem

Nodes are just an ID and a label parsed out of the `.mmd` file. We want richer
per-node context in the details panel: a standing description, a "learn more"
link to another docs page or an external URL, maybe a type/icon — shown whenever
a step targets that node, independent of the step's own `title`/`description`.

## Options — where metadata lives

- **A. Mermaid `click` / `class` directives in the `.mmd`.** `click NODE "url"
  "tooltip"` is native Mermaid. Pro: standard syntax. Con: the parser currently
  rejects `click`/`class`; limited to a URL + tooltip, no structured fields.
- **B. a `nodes:` map in the scenario YAML.**
  ```yaml
  nodes:
    DB: { summary: "Source of truth", doc: "concepts/postgres.md" }
  ```
  Pro: flexible, no parser change. Con: per-scenario — duplicated across
  scenarios that share a topology (see [0001](0001-selectable-scenarios.md)).
- **C. a sidecar metadata file referenced from the directive.**
  ```yaml
  ::: interactive-flow
  diagram: flows/cdc.mmd
  metadata: flows/cdc-nodes.yaml
  scenario: flows/cdc-normal.yaml
  :::
  ```
  Pro: shared by every scenario over that topology, clean separation, own schema.
  Con: another file to wire up.
- **D. a comment / frontmatter block inside the `.mmd`.** Keeps it with the
  topology but needs non-standard parsing.

Leaning **C** (pairs naturally with 0001); **B** if scenarios-sharing-topology
does not land.

## Rendering

- When a node step is active, the details panel shows the node's `summary` plus
  the step's own `description` (see open question 1), and a doc link.
- Links: internal paths resolved like MkDocs links; external forced to
  `target="_blank" rel="noopener noreferrer"`; only `http(s)` and site-relative
  allowed, validated at build.

## Open questions

1. Precedence of step `description` vs node `summary` — replace, or show both
   (node context first, step detail second)?
2. Do edges get metadata too, or nodes only for now?
3. Field set: `summary`, `doc`, `icon`, `type`? Keep it minimal for v1.
4. Should the node label itself become a link in the SVG, or only the panel?
