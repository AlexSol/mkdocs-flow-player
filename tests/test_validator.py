import pytest

from mkdocs_flow_player.parser import Edge, FlowError, Topology
from mkdocs_flow_player.validator import validate_metadata, validate_scenario


TOPOLOGY = Topology("", frozenset({"A", "B"}), (Edge("A", "B", 1),))
PARALLEL = Topology(
    "",
    frozenset({"A", "B"}),
    (Edge("A", "B", 1, "primary"), Edge("A", "B", 2, "retry")),
)


def test_valid_scenario():
    validate_scenario(
        {"id": "ok", "steps": [{"node": "A"}, {"edge": {"from": "A", "to": "B"}}]},
        TOPOLOGY,
    )


def test_unknown_node():
    with pytest.raises(FlowError, match="unknown node 'C'"):
        validate_scenario({"id": "bad", "steps": [{"node": "C"}]}, TOPOLOGY)


def test_valid_metadata():
    validate_metadata(
        {"nodes": {"A": {"summary": "Source node", "doc": "concepts/a.md"}, "B": {}}},
        TOPOLOGY,
    )


@pytest.mark.parametrize("metadata", [
    {"extra": {}},
    {"nodes": []},
    {"nodes": {"C": {"summary": "Unknown"}}},
    {"nodes": {"A": {"summary": 1}}},
    {"nodes": {"A": {"doc": ""}}},
    {"nodes": {"A": {"icon": "db"}}},
])
def test_invalid_metadata(metadata):
    with pytest.raises(FlowError):
        validate_metadata(metadata, TOPOLOGY)


def test_unknown_edge():
    with pytest.raises(FlowError, match="unknown edge 'B->A'"):
        validate_scenario(
            {"id": "bad", "steps": [{"edge": {"from": "B", "to": "A"}}]},
            TOPOLOGY,
        )


def test_parallel_edge_requires_disambiguation():
    with pytest.raises(FlowError, match="ambiguous edge 'A->B'"):
        validate_scenario({"id": "bad", "steps": [{"edge": {"from": "A", "to": "B"}}]}, PARALLEL)


def test_parallel_edge_can_be_selected_by_nth():
    scenario = {"id": "ok", "steps": [{"edge": {"from": "A", "to": "B", "nth": 2}}]}
    validate_scenario(scenario, PARALLEL)
    assert scenario["steps"][0]["edge"] == {"from": "A", "to": "B", "nth": 2, "label": "retry"}


def test_parallel_edge_can_be_selected_by_label():
    scenario = {"id": "ok", "steps": [{"edge": {"from": "A", "to": "B", "label": "primary"}}]}
    validate_scenario(scenario, PARALLEL)
    assert scenario["steps"][0]["edge"] == {"from": "A", "to": "B", "label": "primary", "nth": 1}


def test_parallel_edge_nth_and_label_must_match():
    with pytest.raises(FlowError, match="no matching edge exists"):
        validate_scenario(
            {"id": "bad", "steps": [{"edge": {"from": "A", "to": "B", "nth": 1, "label": "retry"}}]},
            PARALLEL,
        )


def test_duplicate_parallel_labels_are_ambiguous_without_nth():
    topology = Topology(
        "",
        frozenset({"A", "B"}),
        (Edge("A", "B", 1, "retry"), Edge("A", "B", 2, "retry")),
    )
    with pytest.raises(FlowError, match="Add edge.nth"):
        validate_scenario(
            {"id": "bad", "steps": [{"edge": {"from": "A", "to": "B", "label": "retry"}}]},
            topology,
        )


def test_invalid_state():
    with pytest.raises(FlowError, match="invalid state"):
        validate_scenario({"id": "bad", "steps": [{"node": "A", "state": "done"}]}, TOPOLOGY)
