"""JSON-compatible YAML data and HTML-safe script data blocks."""
from datetime import date, datetime
import json
import math

from .parser import FlowError


def json_value(value, ancestors=(), depth=0):
    if depth > 64:
        raise FlowError("Scenario data exceeds 64 nesting levels")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        if id(value) in ancestors:
            raise FlowError("Cyclic YAML aliases are not supported")
        parents = (*ancestors, id(value))
        if isinstance(value, list):
            return [json_value(item, parents, depth + 1) for item in value]
        if not all(isinstance(key, str) for key in value):
            raise FlowError("Scenario object keys must be strings")
        return {key: json_value(item, parents, depth + 1) for key, item in value.items()}
    raise FlowError(f"Unsupported JSON value: {type(value).__name__} (non-finite numbers are not allowed)")


def script_json(value):
    # Escaping every '<' also prevents mixed-case closing tags and <!-- tokens.
    return json.dumps(json_value(value), ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
