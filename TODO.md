# Roadmap

## Done in v0.1 MVP

- [x] Installable Python package and MkDocs entry point (`flow-player`)
- [x] `::: interactive-flow` Markdown directive
- [x] Load Mermaid `.mmd` topology and YAML scenario from `docs_dir`
- [x] Small scenario DSL for node/edge, state, action, title, description and payload
- [x] Strict build-time validation of node and edge references
- [x] Optional `warning` validation mode
- [x] Build-time YAML-to-JSON conversion
- [x] Automatic JS/CSS asset injection
- [x] Browser-side Mermaid rendering
- [x] Reset, Previous, Next and Play/Pause controls
- [x] Node states: active, success, warning, error and waiting
- [x] Animated marker travel along Mermaid edges
- [x] Replay-based Previous/reset behavior
- [x] Multiple players on one page
- [x] Normal replication and target-offline examples
- [x] Parser, validator, renderer and integration tests

## Review fixes (v0.1.1)

- [x] Replace a node's previous CSS state when applying a new state
- [x] Isolate invalid placeholders, constructor errors and rendering failures
- [x] Embed Mermaid as safe JSON; escape warning messages and use strict security
- [x] Parse inline/implicit nodes and chained edges; document supported Mermaid subset
- [x] Leave directives inside fenced and indented code examples untouched
- [x] Validate field types, actions, duration and JSON compatibility; normalize YAML dates
- [x] Freeze/resume both marker animation and step time on Pause/Play
- [x] Add Python regression tests and deterministic JS player tests
- [x] Add real-Mermaid browser smoke test for recovery, playback and error isolation
- [x] Add GitHub Actions CI for Python tests, package build, MkDocs strict build, JS tests and browser smoke

Verification for this patch: **58 Python tests + 7 JS tests passed**, and the
example builds with `mkdocs build --strict`. The browser smoke script is added
but **has not been executed successfully here**: Chromium download timed out,
and the available remote browser blocked the local test URL. Run the README
browser commands locally before declaring end-to-end browser compatibility.

## Next

- [ ] Execute the real-Mermaid browser smoke test in a browser-enabled environment
- [ ] Watch the first GitHub Actions run and fix any runner-specific failures
- [ ] Expand browser coverage across themes, mobile layouts and Material navigation
- [ ] Support Mermaid edge labels and multiple edges between the same nodes robustly
- [ ] Improve Mermaid ID compatibility across Mermaid releases
- [ ] Add selectable scenarios sharing one topology
- [ ] Add node metadata/details and documentation links
- [ ] Add keyboard navigation and richer accessibility semantics
- [ ] Improve responsive layout and theme integration (Material/light/dark)
- [ ] Add a configurable, vendored Mermaid option for offline documentation
- [x] Add JSON Schema and editor autocomplete for the YAML DSL
- [x] Add duplicate flow/scenario ID validation across the site
- [ ] Publish package releases to PyPI with changelog and compatibility matrix

## Explicitly out of scope

- Visual graph editor
- Custom graph layout or SVG renderer
- Backend/runtime service
- Arbitrary JavaScript in scenarios
