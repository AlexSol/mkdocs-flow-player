from __future__ import annotations

from typing import Any

from .parser import ALLOWED_STATES, Edge, FlowError, Topology
from .serialization import json_value


def _describe_edge(edge: Edge) -> str:
    label = f" label={edge.label!r}" if edge.label is not None else ""
    return f"{edge.left}->{edge.right} nth={edge.index}{label}"


def _match_edge(step_index: int, spec: dict[str, Any], topology: Topology) -> Edge:
    left, right = str(spec["from"]), str(spec["to"])
    candidates = [edge for edge in topology.edges if edge.left == left and edge.right == right]
    if not candidates:
        known = ", ".join(_describe_edge(edge) for edge in topology.edges)
        raise FlowError(
            f"Step {step_index} references unknown edge '{left}->{right}'. "
            f"Known edges: {known or '(none)'}"
        )

    nth = spec.get("nth")
    label = spec.get("label")
    matches = candidates
    if nth is not None:
        matches = [edge for edge in matches if edge.index == nth]
    if label is not None:
        matches = [edge for edge in matches if edge.label == label]

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        known = ", ".join(_describe_edge(edge) for edge in matches)
        raise FlowError(
            f"Step {step_index} references ambiguous edge '{left}->{right}'. "
            f"Add edge.nth. Candidates: {known}"
        )

    if nth is not None or label is not None:
        wanted = []
        if nth is not None:
            wanted.append(f"nth={nth}")
        if label is not None:
            wanted.append(f"label={label!r}")
        known = ", ".join(_describe_edge(edge) for edge in candidates)
        raise FlowError(
            f"Step {step_index} references edge '{left}->{right}' with {' and '.join(wanted)}, "
            f"but no matching edge exists. Candidates: {known}"
        )

    if len(candidates) > 1:
        known = ", ".join(_describe_edge(edge) for edge in candidates)
        raise FlowError(
            f"Step {step_index} references ambiguous edge '{left}->{right}'. "
            f"Add edge.nth or edge.label. Candidates: {known}"
        )
    return candidates[0]


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
        if not isinstance(edge, dict) or set(edge) - {"from", "to", "nth", "label"}:
            raise FlowError(f"Step {index} edge requires 'from' and 'to'")
        if any(not isinstance(edge.get(key), str) or not edge[key] for key in ("from", "to")):
            raise FlowError(f"Step {index} edge requires 'from' and 'to'")
        if "nth" in edge and (type(edge["nth"]) is not int or edge["nth"] < 1):
            raise FlowError(f"Step {index} edge.nth must be a positive integer")
        if "label" in edge and (not isinstance(edge["label"], str) or not edge["label"]):
            raise FlowError(f"Step {index} edge.label must be a non-empty string")
        match = _match_edge(index, edge, topology)
        edge["nth"] = match.index
        if match.label is not None and "label" not in edge:
            edge["label"] = match.label
