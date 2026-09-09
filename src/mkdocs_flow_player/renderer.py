from __future__ import annotations

import html
import json
from typing import Any


def render_player(diagram: str, scenario: dict[str, Any]) -> str:
    flow_id = html.escape(str(scenario["id"]), quote=True)
    title = html.escape(str(scenario.get("title", scenario["id"])))
    diagram_text = diagram.replace("</script", "<\\/script")
    scenario_json = json.dumps(scenario, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<div class="flow-player" data-flow-id="{flow_id}">
  <header class="flow-player__header"><strong>{title}</strong></header>
  <script type="text/plain" class="flow-player__mermaid">{diagram_text}</script>
  <script type="application/json" class="flow-player__scenario">{scenario_json}</script>
  <div class="flow-player__canvas" aria-label="{title}"></div>
  <section class="flow-player__details" aria-live="polite">
    <div class="flow-player__counter">Ready</div>
    <h4 class="flow-player__step-title">Select Next to start</h4>
    <p class="flow-player__description"></p>
    <pre class="flow-player__payload" hidden></pre>
  </section>
  <nav class="flow-player__controls" aria-label="Flow controls">
    <button type="button" data-action="reset">Reset</button>
    <button type="button" data-action="previous">Previous</button>
    <button type="button" data-action="next">Next</button>
    <button type="button" data-action="play">Play</button>
  </nav>
</div>"""

