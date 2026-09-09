from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from mkdocs_flow_player.parser import ALLOWED_STATES
from mkdocs_flow_player.schema import scenario_schema

SCHEMA = scenario_schema()
VALIDATOR = Draft202012Validator(SCHEMA)
EXAMPLES = Path(__file__).parents[1] / "example/docs/flows"


def test_schema_is_a_valid_draft_2020_12_schema():
    Draft202012Validator.check_schema(SCHEMA)


def test_state_enum_matches_the_parser():
    assert set(SCHEMA["$defs"]["state"]["enum"]) == ALLOWED_STATES


@pytest.mark.parametrize("name", sorted(path.name for path in EXAMPLES.glob("*.yaml")))
def test_bundled_example_scenarios_conform(name):
    VALIDATOR.validate(yaml.safe_load((EXAMPLES / name).read_text(encoding="utf-8")))


def test_edge_disambiguators_are_valid():
    VALIDATOR.validate({
        "id": "x",
        "steps": [{"edge": {"from": "A", "to": "B", "nth": 2, "label": "retry"}}],
    })


@pytest.mark.parametrize("scenario", [
    {"steps": [{"node": "A"}]},                                   # missing id
    {"id": "x"},                                                   # missing steps
    {"id": "x", "steps": []},                                      # empty steps
    {"id": "x", "steps": [{"node": "A", "extra": 1}]},             # unknown step field
    {"id": "x", "steps": [{"node": "A", "edge": {"from": "A", "to": "B"}}]},  # both
    {"id": "x", "steps": [{}]},                                    # neither
    {"id": "x", "steps": [{"node": "A", "action": "travel"}]},     # action on node
    {"id": "x", "steps": [{"edge": {"from": "A", "to": "B"}, "state": "active"}]},  # state on edge
    {"id": "x", "steps": [{"node": "A", "state": "done"}]},        # bad state
    {"id": "x", "settings": {"step_duration": 0}, "steps": [{"node": "A"}]},   # duration too small
    {"id": "x", "settings": {"step_duration": 1.5}, "steps": [{"node": "A"}]}, # non-integer
    {"id": "  ", "steps": [{"node": "A"}]},                        # blank id
    {"id": "x", "title": 5, "steps": [{"node": "A"}]},             # non-string title
    {"id": "x", "steps": [{"edge": {"from": "A"}}]},               # edge missing "to"
    {"id": "x", "steps": [{"edge": {"from": "A", "to": "B", "nth": 0}}]},     # bad nth
    {"id": "x", "steps": [{"edge": {"from": "A", "to": "B", "label": ""}}]},  # blank label
])
def test_invalid_scenarios_are_rejected(scenario):
    assert not VALIDATOR.is_valid(scenario)
