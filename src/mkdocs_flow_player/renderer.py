from __future__ import annotations

import html
from typing import Any
from .serialization import script_json


def render_player(diagram: str, scenario: dict[str, Any]) -> str:
    flow_id = html.escape(str(scenario["id"]), quote=True)
    title = html.escape(str(scenario.get("title", scenario["id"])))
    diagram_text = script_json(diagram)
    scenario_json = script_json(scenario)
    return f"""<div class="flow-player" data-flow-id="{flow_id}" role="group" aria-roledescription="Interactive flow" aria-label="{title}">
  <header class="flow-player__header"><strong>{title}</strong></header>
  <script type="application/json" class="flow-player__mermaid">{diagram_text}</script>
  <script type="application/json" class="flow-player__scenario">{scenario_json}</script>
  <div class="flow-player__canvas" role="img" tabindex="0" aria-label="{title} diagram"></div>
  <nav class="flow-player__controls" aria-label="Flow controls">
    <button type="button" data-action="reset">Reset</button>
    <button type="button" data-action="previous" aria-keyshortcuts="ArrowLeft Home">Previous</button>
    <button type="button" data-action="next" aria-keyshortcuts="ArrowRight End">Next</button>
    <button type="button" data-action="play">Play</button>
  </nav>
  <section class="flow-player__details" aria-live="polite">
    <div class="flow-player__counter">Ready</div>
    <h4 class="flow-player__step-title">Select Next to start</h4>
    <p class="flow-player__description"></p>
    <pre class="flow-player__payload" hidden></pre>
  </section>
</div>"""
