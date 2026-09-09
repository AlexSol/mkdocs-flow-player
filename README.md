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

`state` defaults to `active` on node steps. Edge steps accept only `action: travel`
(also the default). Each step contains exactly one of `node` or `edge`.
`title` and `description` must be strings; `step_duration` is an integer from
1 to 600000 milliseconds (default 1500). Unknown fields and invalid types are
reported as flow validation errors, including in `warning` mode.

Payload accepts JSON-compatible values, including `false`, `0` and `null`.
YAML dates/timestamps become ISO strings; NaN/Infinity, binary values, sets,
non-string object keys, cyclic aliases and nesting beyond 64 levels are rejected.

### Supported Mermaid syntax

The build-time validator deliberately supports a **flowchart subset**, not every
Mermaid diagram type. Use `flowchart` or `graph` with `LR`, `RL`, `TB`, `TD` or `BT`
on its own line (or followed by a semicolon). Node IDs use ASCII letters, digits,
underscores and internal hyphens, beginning with a letter or underscore.

Supported forms include separate node declarations, implicit nodes, inline node
shapes and chains, for example:

```text
flowchart LR
    A[Source] -->|event| B[(Queue)] --> C[Consumer]
    C -.-> A
```

Supported links: `-->`, `-.->`, `==>`, `---`, `--o`, `--x`, with optional `|label|`.
Common bracket-based shapes (`[]`, `()`, `(())`, `[()]`, `{}`, `{{}}`, `[[]]`)
and double-quoted labels are supported. Keep complex label text double-quoted;
use Mermaid entities for embedded quotes. Newlines/semicolons separate statements;
`%%` comments are accepted. Do not put unquoted semicolons in edge labels.

Subgraphs, grouped links (`A & B`), class/style/click statements, custom edge IDs,
frontmatter, and new `@{...}` shape syntax are not supported in this version.
Parallel edges between the same ordered pair are rejected because `from`/`to`
cannot identify one unambiguously. Unsupported syntax fails with a readable error.

The Markdown directive is top-level; examples inside backtick/tilde fences or
indented code blocks remain literal. Source and scenario data are embedded as
HTML-safe JSON, warning messages are escaped, and Mermaid uses strict security.
This does not sandbox the rest of a MkDocs site: publish only reviewed documentation.

### Playback

- Each node has exactly one current state; the last applicable step wins.
- Previous/Reset rebuild the state without replaying travel animations.
- Pause freezes both the marker and the step clock; Play resumes the same step.
- Manual Next/Previous stops autoplay. Play after completed autoplay restarts.
- A failed player does not prevent other players on the page from initializing.

### Tests

```bash
pytest -q
node --test tests/js/*.test.cjs
mkdocs build -f example/mkdocs.yml --strict
```

The JavaScript unit tests use Node's built-in runner and a deterministic clock
(no npm installation needed). For browser smoke tests against real Mermaid:

```bash
npm install
npx playwright install chromium
npm run test:browser
```

The browser test expects the built example and downloads Mermaid through the same
CDN URL as the example. For an offline run, set `MERMAID_TEST_SCRIPT` to a local
copy of that upstream script. `CHROMIUM_EXECUTABLE` optionally selects an installed
Chromium binary. The npm dependencies are development-only, not plugin runtime
dependencies. The CDN is pinned to Mermaid 11.17.2; override
`mermaid_url` in the plugin config to use another compatible build.

## Design constraints

- Mermaid owns graph layout and SVG rendering.
- Python handles integration, loading, validation and HTML generation.
- JavaScript handles playback and animation.
- YAML is converted to JSON at build time.
- No React, React Flow, JointJS, D3, backend or browser-side YAML parser.

See [TODO.md](TODO.md) for current status and the roadmap.
