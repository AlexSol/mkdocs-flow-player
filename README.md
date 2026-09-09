# MkDocs Flow Player

Turn Mermaid diagrams into step-by-step executable documentation.

MkDocs Flow Player combines a Mermaid topology with a small YAML scenario DSL.
The MkDocs plugin validates references during the build and embeds a vanilla-JS
player with Reset, Previous, Next and Play/Pause controls.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
mkdocs serve -f example/mkdocs.yml
```

Open <http://127.0.0.1:8000>.

Enable the plugin in `mkdocs.yml`:

```yaml
plugins:
  - search
  - flow-player:
      validation: strict
```

Add a flow to a Markdown page:

```text
::: interactive-flow
diagram: flows/cdc.mmd
scenario: flows/cdc-normal.yaml
:::
```

Paths are resolved from `docs_dir`. Mermaid node IDs are the public API used by
the scenario. A broken node or edge reference fails `mkdocs build` in strict mode.

## Scenario DSL (v0.1)

```yaml
id: normal-replication
title: Normal replication
settings:
  step_duration: 1500
steps:
  - node: DB
    state: active
    title: Transaction committed
  - edge:
      from: DB
      to: CDC
    action: travel
    title: WAL change
```

Supported states: `active`, `success`, `warning`, `error`, `waiting`.

## Design constraints

- Mermaid owns graph layout and SVG rendering.
- Python handles integration, loading, validation and HTML generation.
- JavaScript handles playback and animation.
- YAML is converted to JSON at build time.
- No React, React Flow, JointJS, D3, backend or browser-side YAML parser.

See [TODO.md](TODO.md) for current status and the roadmap.

