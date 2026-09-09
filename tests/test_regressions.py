from datetime import date
from html.parser import HTMLParser
import json
from types import SimpleNamespace

import pytest
import yaml
from mkdocs.exceptions import PluginError

from mkdocs_flow_player.parser import FlowError, parse_topology, replace_directives
from mkdocs_flow_player.plugin import FlowPlayerPlugin
from mkdocs_flow_player.renderer import render_player
from mkdocs_flow_player.serialization import script_json
from mkdocs_flow_player.validator import validate_scenario


TOPOLOGY = parse_topology("flowchart LR\nA --> B")


@pytest.mark.parametrize("body", [
    "A[One] --> B[Two]", "A --> B", "A[One]\nB[Two]\nA --> B",
    "A[(One)] -->|event| B{{Two}}", 'A["fake --> C; (quoted)"] --> B',
])
def test_inline_and_implicit_nodes(body):
    topology = parse_topology("flowchart LR\n" + body)
    assert topology.nodes == {"A", "B"}
    assert topology.edges == {("A", "B")}


def test_chains_comments_and_semicolons():
    topology = parse_topology("%% comment\nflowchart LR; A --> B[Two] --> C; C -.-> A %% comment\n")
    assert topology.nodes == {"A", "B", "C"}
    assert topology.edges == {("A", "B"), ("B", "C"), ("C", "A")}


@pytest.mark.parametrize("body", ["A & B --> C", "A --> B\nA --> B", "subgraph Group\nA --> B\nend", 'A["unterminated]'])
def test_unsupported_syntax_has_readable_error(body):
    with pytest.raises(FlowError):
        parse_topology("flowchart LR\n" + body)


@pytest.mark.parametrize("fence", ["```", "````", "~~~", "~~~~"])
def test_fenced_directives_are_literal(fence):
    directive = "::: interactive-flow\ndiagram: a.mmd\nscenario: a.yaml\n:::\n"
    source = f"{fence}text\n{directive}{fence}\n\n{directive}"
    calls = []
    def render(body):
        calls.append(body)
        return "PLAYER"
    result = replace_directives(source, render)
    assert len(calls) == 1
    assert result == f"{fence}text\n{directive}{fence}\n\nPLAYER\n"


def test_indented_and_unclosed_code_fences():
    source = "```text\n::: interactive-flow\ndiagram: a\nscenario: b\n:::\n"
    assert replace_directives(source, lambda _: pytest.fail("rendered code")) == source
    source = "    ::: interactive-flow\n    diagram: a\n    scenario: b\n    :::\n"
    assert replace_directives(source, lambda _: pytest.fail("rendered code")) == source


class InspectHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.scripts = []
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "script":
            self.in_script = True
            self.scripts.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.scripts[-1] += data


@pytest.mark.parametrize("closing", ["</script>", "</SCRIPT>", "</ScRiPt>", "<!--<script>"])
def test_script_data_roundtrips_without_html_injection(closing):
    source = f'flowchart LR\nA["{closing}<img src=x onerror=alert(1)>"]'
    scenario = {"id": "x", "steps": [{"node": "A", "payload": closing}]}
    parsed = InspectHTML()
    parsed.feed(render_player(source, scenario))
    assert "img" not in parsed.tags
    assert len(parsed.scripts) == 2
    assert json.loads(parsed.scripts[0]) == source
    assert json.loads(parsed.scripts[1]) == scenario


@pytest.mark.parametrize("step", [
    {"node": ["A"]}, {"node": "A", "state": []}, {"node": "A", "state": None},
    {"edge": {"from": [], "to": "B"}}, {"node": "A", "description": {}},
    {"edge": {"from": "A", "to": "B"}, "action": "teleport"},
    {"node": "A", "action": "travel"}, {"node": "A", "stat": "error"},
])
def test_invalid_steps_raise_flowerror(step):
    with pytest.raises(FlowError):
        validate_scenario({"id": "x", "steps": [step]}, TOPOLOGY)


@pytest.mark.parametrize("duration", [-1, 0, True, "1000", 1.5, None, 600001])
def test_duration_contract(duration):
    with pytest.raises(FlowError, match="step_duration"):
        validate_scenario({"id": "x", "steps": [{"node": "A"}], "settings": {"step_duration": duration}}, TOPOLOGY)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {1, 2}, {1: "key"}, b"bytes"])
def test_non_json_payloads_rejected(value):
    with pytest.raises(FlowError):
        validate_scenario({"id": "x", "steps": [{"node": "A", "payload": value}]}, TOPOLOGY)


def test_dates_normalize_and_cycles_fail():
    assert json.loads(script_json({"day": date(2026, 9, 9)})) == {"day": "2026-09-09"}
    scenario = yaml.safe_load("id: x\nsteps:\n- node: A\n  payload:\n    day: 2026-09-09")
    validate_scenario(scenario, TOPOLOGY)
    assert "2026-09-09" in render_player(TOPOLOGY.source, scenario)
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(FlowError, match="Cyclic"):
        script_json(cyclic)


@pytest.mark.parametrize("mode", ["warning", "strict"])
@pytest.mark.parametrize("scenario", [
    "id: x\nsteps:\n- node: [A]", "id: x\nsteps:\n- node: A\n  state: []",
    "id: x\nsettings: {step_duration: -1}\nsteps:\n- node: A",
    "id: x\nsteps:\n- node: A\n  payload: .nan",
])
def test_validation_modes_handle_malformed_data(tmp_path, mode, scenario):
    (tmp_path / "a.mmd").write_text("flowchart LR\nA --> B")
    (tmp_path / "a.yaml").write_text(scenario)
    plugin = FlowPlayerPlugin()
    plugin.load_config({"validation": mode})
    args = ("::: interactive-flow\ndiagram: a.mmd\nscenario: a.yaml\n:::",
            SimpleNamespace(file=SimpleNamespace(src_path="index.md")),
            SimpleNamespace(docs_dir=str(tmp_path)), None)
    if mode == "strict":
        with pytest.raises(PluginError):
            plugin.on_page_markdown(*args)
    else:
        result = plugin.on_page_markdown(*args)
        assert 'role="alert"' in result
        assert 'class="flow-player"' not in result


def test_warning_message_escaped(tmp_path):
    plugin = FlowPlayerPlugin()
    plugin.load_config({"validation": "warning"})
    source = '::: interactive-flow\ndiagram: "<img src=x onerror=alert(1)>.mmd"\nscenario: a.yaml\n:::'
    output = plugin.on_page_markdown(source, SimpleNamespace(file=SimpleNamespace(src_path="index.md")), SimpleNamespace(docs_dir=str(tmp_path)), None)
    parsed = InspectHTML()
    parsed.feed(output)
    assert "img" not in parsed.tags
    assert "&lt;img" in output
