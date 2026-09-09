from __future__ import annotations

from typing import Any

from .parser import ALLOWED_STATES, FlowError, Topology


def validate_scenario(scenario: dict[str, Any], topology: Topology) -> None:
    flow_id = scenario.get("id")
    if not isinstance(flow_id, str) or not flow_id.strip():
        raise FlowError("Scenario requires a non-empty string 'id'")

    steps = scenario.get("steps")
    if not isinstance(steps, list) or not steps:
        raise FlowError("Scenario requires a non-empty 'steps' list")

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise FlowError(f"Step {index} must be a mapping")
        has_node = "node" in step
        has_edge = "edge" in step
        if has_node == has_edge:
            raise FlowError(f"Step {index} must contain exactly one of 'node' or 'edge'")

        state = step.get("state")
        if state is not None and state not in ALLOWED_STATES:
            allowed = ", ".join(sorted(ALLOWED_STATES))
            raise FlowError(f"Step {index} has invalid state '{state}'. Allowed: {allowed}")

        if has_node:
            node = step["node"]
            if node not in topology.nodes:
                known = ", ".join(sorted(topology.nodes))
                raise FlowError(
                    f"Step {index} references unknown node '{node}'. Known nodes: {known}"
                )
            continue

        edge = step["edge"]
        if not isinstance(edge, dict) or not edge.get("from") or not edge.get("to"):
            raise FlowError(f"Step {index} edge requires 'from' and 'to'")
        pair = (str(edge["from"]), str(edge["to"]))
        if pair not in topology.edges:
            known = ", ".join(f"{left}->{right}" for left, right in sorted(topology.edges))
            raise FlowError(
                f"Step {index} references unknown edge '{pair[0]}->{pair[1]}'. "
                f"Known edges: {known or '(none)'}"
            )

