import pytest

from mkdocs_flow_player.parser import FlowError, Topology
from mkdocs_flow_player.validator import validate_scenario


TOPOLOGY = Topology("", frozenset({"A", "B"}), frozenset({("A", "B")}))


def test_valid_scenario():
    validate_scenario(
        {"id": "ok", "steps": [{"node": "A"}, {"edge": {"from": "A", "to": "B"}}]},
        TOPOLOGY,
    )


def test_unknown_node():
    with pytest.raises(FlowError, match="unknown node 'C'"):
        validate_scenario({"id": "bad", "steps": [{"node": "C"}]}, TOPOLOGY)


def test_unknown_edge():
    with pytest.raises(FlowError, match="unknown edge 'B->A'"):
        validate_scenario(
            {"id": "bad", "steps": [{"edge": {"from": "B", "to": "A"}}]},
            TOPOLOGY,
        )


def test_invalid_state():
    with pytest.raises(FlowError, match="invalid state"):
        validate_scenario({"id": "bad", "steps": [{"node": "A", "state": "done"}]}, TOPOLOGY)

