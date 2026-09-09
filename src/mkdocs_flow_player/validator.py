from __future__ import annotations

from typing import Any

from .parser import ALLOWED_STATES, FlowError, Topology
from .serialization import json_value


def validate_scenario(scenario: dict[str, Any], topology: Topology) -> None:
    if not isinstance(scenario, dict):
        raise FlowError("Scenario must be a mapping")
    json_value(scenario)
    if set(scenario) - {"id", "title", "settings", "steps"}:
        raise FlowError("Unknown scenario field; expected id, title, settings or steps")
    flow_id = scenario.get("id")
    if not isinstance(flow_id, str) or not flow_id.strip():
        raise FlowError("Scenario requires a non-empty string 'id'")
    if "title" in scenario and not isinstance(scenario["title"], str):
        raise FlowError("Scenario title must be a string")
    settings = scenario.get("settings", {})
    if not isinstance(settings, dict) or set(settings) - {"step_duration"}:
        raise FlowError("settings must be a mapping containing only step_duration")
    duration = settings.get("step_duration", 1500)
    if type(duration) is not int or not 1 <= duration <= 600000:
        raise FlowError("step_duration must be an integer between 1 and 600000 milliseconds")

    steps = scenario.get("steps")
    if not isinstance(steps, list) or not steps:
        raise FlowError("Scenario requires a non-empty 'steps' list")

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise FlowError(f"Step {index} must be a mapping")
        if set(step) - {"node", "edge", "state", "action", "title", "description", "payload"}:
            raise FlowError(f"Step {index} contains unknown fields")
        for field in ("title", "description"):
            if field in step and not isinstance(step[field], str):
                raise FlowError(f"Step {index} {field} must be a string")
        has_node = "node" in step
        has_edge = "edge" in step
        if has_node == has_edge:
            raise FlowError(f"Step {index} must contain exactly one of 'node' or 'edge'")

        state = step.get("state")
        if "state" in step and (not isinstance(state, str) or state not in ALLOWED_STATES):
            allowed = ", ".join(sorted(ALLOWED_STATES))
            raise FlowError(f"Step {index} has invalid state '{state}'. Allowed: {allowed}")

        if has_node:
            node = step["node"]
            if "action" in step:
                raise FlowError(f"Step {index}: action is only allowed for edge steps")
            if not isinstance(node, str):
                raise FlowError(f"Step {index} node must be a string")
            if node not in topology.nodes:
                known = ", ".join(sorted(topology.nodes))
                raise FlowError(
                    f"Step {index} references unknown node '{node}'. Known nodes: {known}"
                )
            continue

        edge = step["edge"]
        if "state" in step:
            raise FlowError(f"Step {index}: state is only allowed for node steps")
        if step.get("action", "travel") != "travel":
            raise FlowError(f"Step {index} action must be travel")
        if (not isinstance(edge, dict) or set(edge) != {"from", "to"}
                or any(not isinstance(edge.get(key), str) or not edge[key] for key in ("from", "to"))):
            raise FlowError(f"Step {index} edge requires 'from' and 'to'")
        pair = (str(edge["from"]), str(edge["to"]))
        if pair not in topology.edges:
            known = ", ".join(f"{left}->{right}" for left, right in sorted(topology.edges))
            raise FlowError(
                f"Step {index} references unknown edge '{pair[0]}->{pair[1]}'. "
                f"Known edges: {known or '(none)'}"
            )
