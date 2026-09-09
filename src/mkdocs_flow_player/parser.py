from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable

import yaml


ALLOWED_STATES = {"active", "success", "warning", "error", "waiting"}
IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:-[A-Za-z0-9_]+)*")
LINK_RE = re.compile(r"(?:-->|-\.->|==>|--o|--x|---)")


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
    if set(data) - {"diagram", "scenario"}:
        raise FlowError("Unknown directive field; expected diagram and scenario")
    if any(not isinstance(data[key], str) for key in ("diagram", "scenario")):
        raise FlowError("diagram and scenario paths must be strings")
    return Directive(diagram=data["diagram"], scenario=data["scenario"])


def replace_directives(markdown: str, render: Callable[[str], str]) -> str:
    """Only process top-level directives, never fenced/indented code examples."""
    lines = markdown.splitlines(keepends=True)
    result = []
    fence = None
    index = 0
    while index < len(lines):
        line = lines[index]
        if fence:
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) +
                            r"{" + str(len(fence)) + r",}[ \t]*\n?", line):
                fence = None
        else:
            opening = re.match(r" {0,3}(`{3,}|~{3,})", line)
            if opening:
                fence = opening[1]
            elif re.fullmatch(r" {0,3}:::[ \t]*interactive-flow[ \t]*\n?", line):
                end = index + 1
                while end < len(lines) and not re.fullmatch(r" {0,3}:::[ \t]*\n?", lines[end]):
                    end += 1
                if end < len(lines):
                    result.append(render("".join(lines[index + 1:end])) + "\n")
                    index = end + 1
                    continue
        result.append(line)
        index += 1
    return "".join(result)


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise FlowError(f"Cannot read scenario {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise FlowError(f"Invalid scenario YAML {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise FlowError(f"Scenario must be a YAML mapping: {path}")
    return data


def load_topology(path: Path) -> Topology:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise FlowError(f"Cannot read diagram {path}: {exc}") from exc
    try:
        return parse_topology(source)
    except FlowError as exc:
        raise FlowError(f"{path}: {exc}") from exc


def _statements(source: str) -> list[str]:
    # Split only outside shapes and quoted labels. Arrow-looking label text is data.
    statements, buffer, stack = [], [], []
    quote = False
    index = 0
    pairs = {"[": "]", "(": ")", "{": "}"}
    while index < len(source):
        char = source[index]
        if not quote and not stack and source[index:index + 2] == "%%":
            index = source.find("\n", index)
            if index < 0:
                break
            continue
        if char == '"':
            quote = not quote
        elif not quote:
            if char in pairs:
                stack.append(pairs[char])
            elif char in "])}":
                if not stack or stack.pop() != char:
                    raise FlowError("Unbalanced Mermaid shape")
            elif char in "\n;" and not stack:
                if "".join(buffer).strip():
                    statements.append("".join(buffer).strip())
                buffer = []
                index += 1
                continue
        buffer.append(char)
        index += 1
    if quote or stack:
        raise FlowError("Unterminated Mermaid shape or quoted label")
    if "".join(buffer).strip():
        statements.append("".join(buffer).strip())
    return statements


def _node(text: str, offset: int) -> tuple[str, int]:
    while offset < len(text) and text[offset].isspace():
        offset += 1
    match = IDENTIFIER_RE.match(text, offset)
    if not match:
        raise FlowError(f"Expected node ID near: {text[offset:]}")
    node, offset = match[0], match.end()
    while offset < len(text) and text[offset].isspace():
        offset += 1
    if offset < len(text) and text[offset] in "[({":
        stack, quote = [], False
        pairs = {"[": "]", "(": ")", "{": "}"}
        while offset < len(text):
            char = text[offset]
            offset += 1
            if char == '"':
                quote = not quote
            elif not quote:
                if char in pairs:
                    stack.append(pairs[char])
                elif char in "])}":
                    if not stack or stack.pop() != char:
                        raise FlowError("Unbalanced Mermaid shape")
                    if not stack:
                        break
    return node, offset


def parse_topology(source: str) -> Topology:
    """Validate a documented flowchart subset, not the full Mermaid grammar."""
    statements = _statements(source)
    if not statements or not re.fullmatch(r"(?:flowchart|graph)\s+(?:LR|RL|TB|TD|BT)", statements[0]):
        raise FlowError("Expected flowchart/graph LR, RL, TB, TD or BT on its own line")
    nodes, edges = set(), set()
    for statement in statements[1:]:
        left, offset = _node(statement, 0)
        nodes.add(left)
        while statement[offset:].strip():
            while offset < len(statement) and statement[offset].isspace():
                offset += 1
            link = LINK_RE.match(statement, offset)
            if not link:
                raise FlowError(f"Unsupported Mermaid syntax near: {statement[offset:]}. See README syntax contract")
            offset = link.end()
            while offset < len(statement) and statement[offset].isspace():
                offset += 1
            if offset < len(statement) and statement[offset] == "|":
                end = statement.find("|", offset + 1)
                if end < 0:
                    raise FlowError("Unterminated edge label")
                offset = end + 1
            right, offset = _node(statement, offset)
            nodes.add(right)
            if (left, right) in edges:
                raise FlowError(f"Parallel edge {left}->{right} is ambiguous in the current DSL")
            edges.add((left, right))
            left = right
    if not nodes:
        raise FlowError("No Mermaid nodes found")
    return Topology(source, frozenset(nodes), frozenset(edges))
