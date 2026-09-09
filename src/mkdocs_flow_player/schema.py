"""Access to the packaged JSON Schema for the scenario DSL.

The schema describes the shape of a scenario YAML file for editors and other
tools. It does not (and cannot) check that node IDs and edges resolve against a
topology -- `validator.validate_scenario` does that during `mkdocs build`.
"""
from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

#: Stable URL for editors, e.g. `# yaml-language-server: $schema=<this>`.
SCHEMA_URL = (
    "https://raw.githubusercontent.com/AlexSol/mkdocs-flow-player/main/"
    "src/mkdocs_flow_player/schema/scenario.schema.json"
)


def scenario_schema() -> dict[str, Any]:
    """Return the parsed scenario JSON Schema shipped with the package."""
    resource = files("mkdocs_flow_player").joinpath("schema/scenario.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))
