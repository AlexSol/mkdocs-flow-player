from __future__ import annotations

import html
from typing import Any
from .serialization import script_json


def _scenario_title(scenario: dict[str, Any]) -> str:
    return str(scenario.get("title", scenario["id"]))


def render_player(diagram: str, scenarios: dict[str, Any] | list[dict[str, Any]], title: str | None = None) -> str:
    scenario_list = [scenarios] if isinstance(scenarios, dict) else scenarios
    current = scenario_list[0]
    flow_id = html.escape(str(current["id"]), quote=True)
    heading = html.escape(str(title) if title is not None else _scenario_title(current))
    scenario_options = ""
    if len(scenario_list) > 1:
        options = "\n".join(
            f'      <option value="{index}">{html.escape(_scenario_title(scenario))}</option>'
            for index, scenario in enumerate(scenario_list)
        )
        scenario_options = f"""
    <label class="flow-player__scenario-picker">
      <span>Scenario</span>
      <select class="flow-player__scenario-select">{options}</select>
    </label>"""
    diagram_text = script_json(diagram)
    scenario_json = script_json(scenario_list if len(scenario_list) > 1 else current)
    return f"""<div class="flow-player" data-flow-id="{flow_id}" role="group" aria-roledescription="Interactive flow" aria-label="{heading}">
  <header class="flow-player__header"><strong class="flow-player__title">{heading}</strong>{scenario_options}</header>
  <script type="application/json" class="flow-player__mermaid">{diagram_text}</script>
  <script type="application/json" class="flow-player__scenario">{scenario_json}</script>
  <div class="flow-player__canvas" role="img" tabindex="0" aria-label="{heading} diagram"></div>
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
