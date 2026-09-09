from pathlib import Path

import pytest

from mkdocs_flow_player.parser import Edge, FlowError, load_topology, parse_directive


def test_parse_directive():
    directive = parse_directive("diagram: flows/a.mmd\nscenario: flows/a.yaml")
    assert directive.diagram == "flows/a.mmd"
    assert directive.scenario == "flows/a.yaml"
    assert directive.scenarios == ("flows/a.yaml",)


def test_parse_directive_with_scenarios():
    directive = parse_directive("title: Demo\ndiagram: flows/a.mmd\nmetadata: flows/nodes.yaml\nscenarios:\n- flows/a.yaml\n- flows/b.yaml")
    assert directive.diagram == "flows/a.mmd"
    assert directive.title == "Demo"
    assert directive.metadata == "flows/nodes.yaml"
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


def test_load_sequence_topology(tmp_path: Path):
    diagram = tmp_path / "sequence.mmd"
    diagram.write_text(
        "sequenceDiagram\n"
        "    Alice->>+John: Hello John, how are you?\n"
        "    Alice->>+John: John, can you hear me?\n"
        "    John-->>-Alice: Hi Alice, I can hear you!\n"
        "    John-->>-Alice: I feel great!\n"
    )
    topology = load_topology(diagram)
    assert topology.nodes == {"Alice", "John"}
    assert topology.edges == (
        Edge("Alice", "John", 1, "Hello John, how are you?"),
        Edge("Alice", "John", 2, "John, can you hear me?"),
        Edge("John", "Alice", 1, "Hi Alice, I can hear you!"),
        Edge("John", "Alice", 2, "I feel great!"),
    )
