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

## Next

- [ ] Add browser unit tests for player state transitions and playback
- [ ] Add Playwright end-to-end tests against the example site
- [ ] Support Mermaid edge labels and multiple edges between the same nodes robustly
- [ ] Improve Mermaid ID compatibility across Mermaid releases
- [ ] Add selectable scenarios sharing one topology
- [ ] Add node metadata/details and documentation links
- [ ] Add keyboard navigation and richer accessibility semantics
- [ ] Improve responsive layout and theme integration (Material/light/dark)
- [ ] Add a configurable, vendored Mermaid option for offline documentation
- [ ] Add JSON Schema and editor autocomplete for the YAML DSL
- [ ] Add duplicate flow/scenario ID validation across the site
- [ ] Publish package releases to PyPI with changelog and compatibility matrix

## Explicitly out of scope

- Visual graph editor
- Custom graph layout or SVG renderer
- Backend/runtime service
- Arbitrary JavaScript in scenarios

