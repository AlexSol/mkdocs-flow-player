from pathlib import Path

import pytest

from mkdocs_flow_player.parser import Edge, FlowError, load_topology, parse_directive


def test_parse_directive():
    directive = parse_directive("diagram: flows/a.mmd\nscenario: flows/a.yaml")
    assert directive.diagram == "flows/a.mmd"
    assert directive.scenario == "flows/a.yaml"
    assert directive.scenarios == ("flows/a.yaml",)


def test_parse_directive_with_scenarios():
    directive = parse_directive("title: Demo\ndiagram: flows/a.mmd\nscenarios:\n- flows/a.yaml\n- flows/b.yaml")
    assert directive.diagram == "flows/a.mmd"
    assert directive.title == "Demo"
    assert directive.scenario == "flows/a.yaml"
    assert directive.scenarios == ("flows/a.yaml", "flows/b.yaml")


def test_directive_requires_both_files():
    with pytest.raises(FlowError, match="missing: scenario"):
        parse_directive("diagram: flows/a.mmd")


def test_directive_rejects_mixed_scenario_forms():
    with pytest.raises(FlowError, match="either scenario or scenarios"):
        parse_directive("diagram: flows/a.mmd\nscenario: flows/a.yaml\nscenarios:\n- flows/b.yaml")


def test_load_topology(tmp_path: Path):
    diagram = tmp_path / "flow.mmd"
    diagram.write_text("flowchart LR\n A[One]\n B[Two]\n A -->|event| B\n")
    topology = load_topology(diagram)
    assert topology.nodes == {"A", "B"}
    assert topology.edges == (Edge("A", "B", 1, "event"),)
