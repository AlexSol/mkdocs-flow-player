from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml


ALLOWED_STATES = {"active", "success", "warning", "error", "waiting"}
DIRECTIVE_RE = re.compile(
    r"^:::\s*interactive-flow\s*\n(?P<body>.*?)^:::\s*$",
    re.MULTILINE | re.DOTALL,
)
NODE_RE = re.compile(
    r"(?m)^\s*([A-Za-z_][\w-]*)\s*(?=\[\(|\[\[|\[\{|\(\(|\{\{|\[|\(|\{)"
)
EDGE_RE = re.compile(
    r"(?m)^\s*([A-Za-z_][\w-]*)[^\n]*?"
    r"(?:-->|-\.->|==>|--o|--x|---)\s*(?:\|[^|]*\|\s*)?"
    r"([A-Za-z_][\w-]*)"
)


class FlowError(ValueError):
    """A readable build-time error in a flow definition."""


@dataclass(frozen=True)
class Directive:
    diagram: str
    scenario: str


@dataclass(frozen=True)
class Topology:
    source: str
    nodes: frozenset[str]
    edges: frozenset[tuple[str, str]]


def parse_directive(body: str) -> Directive:
    try:
        data = yaml.safe_load(body)
    except yaml.YAMLError as exc:
        raise FlowError(f"Invalid interactive-flow directive: {exc}") from exc
    if not isinstance(data, dict):
        raise FlowError("interactive-flow directive must be a mapping")
    missing = [key for key in ("diagram", "scenario") if not data.get(key)]
    if missing:
        raise FlowError(f"interactive-flow directive is missing: {', '.join(missing)}")
    return Directive(diagram=str(data["diagram"]), scenario=str(data["scenario"]))


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FlowError(f"Scenario file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise FlowError(f"Invalid scenario YAML {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise FlowError(f"Scenario must be a YAML mapping: {path}")
    return data


def load_topology(path: Path) -> Topology:
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FlowError(f"Diagram file not found: {path}") from exc
    nodes = frozenset(NODE_RE.findall(source))
    edges = frozenset(EDGE_RE.findall(source))
    if not nodes:
        raise FlowError(f"No Mermaid node declarations found in: {path}")
    return Topology(source=source, nodes=nodes, edges=edges)

