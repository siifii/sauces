#!/usr/bin/env python3
"""Validate a JSON file against a small JSON-Schema subset (Sauces).

Stdlib only. Supported keywords: type (string or list), properties, required,
items, enum, pattern, minimum, maximum, additionalProperties (false only), and
if/then/else (when DATA is valid against `if`, it must be valid against `then`, else
against `else`).
Annotation keys $schema, title, description are ignored. Any other keyword is
a usage error (exit 2), so an unsupported schema never passes silently.

Exit codes: 0 valid, 1 invalid (one `path: message` line per error on stdout),
2 usage error, unsupported keyword, or unreadable / non-JSON file.
"""
import argparse
import json
import re
import sys

ANNOTATIONS = {"$schema", "title", "description"}
SUPPORTED = {"type", "properties", "required", "items", "enum", "pattern",
             "minimum", "maximum", "additionalProperties", "if", "then", "else"}


class SchemaError(Exception):
    pass


def _is_type(value, name):
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "integer":
        if isinstance(value, bool):
            return False
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    raise SchemaError(f"unknown type: {name}")


def _join(path, key):
    if isinstance(key, int):
        return f"{path}[{key}]"
    return f"{path}.{key}" if path else key


TYPES = {"object", "array", "string", "boolean", "null", "number", "integer"}


def check_schema(schema, path="schema"):
    """Recursively verify the schema itself; raise SchemaError on anything unsupported or malformed."""
    if not isinstance(schema, dict):
        raise SchemaError(f"{path}: schema must be a JSON object")
    for kw in schema:
        if kw not in SUPPORTED and kw not in ANNOTATIONS:
            raise SchemaError(f"unsupported keyword: {kw} (at {path})")
    if "type" in schema:
        t = schema["type"]
        ts = t if isinstance(t, list) else [t]
        if not ts or not all(isinstance(x, str) and x in TYPES for x in ts):
            raise SchemaError(f"{path}: invalid type {json.dumps(t)}")
    if "enum" in schema and not isinstance(schema["enum"], list):
        raise SchemaError(f"{path}: enum must be a list")
    if "required" in schema:
        r = schema["required"]
        if not isinstance(r, list) or not all(isinstance(x, str) for x in r):
            raise SchemaError(f"{path}: required must be a list of strings")
    if "pattern" in schema:
        try:
            re.compile(schema["pattern"])
        except (re.error, TypeError) as e:
            raise SchemaError(f"{path}: invalid pattern: {e}")
    for kw in ("minimum", "maximum"):
        if kw in schema and (isinstance(schema[kw], bool) or not isinstance(schema[kw], (int, float))):
            raise SchemaError(f"{path}: {kw} must be a number")
    if "properties" in schema:
        props = schema["properties"]
        if not isinstance(props, dict):
            raise SchemaError(f"{path}: properties must be an object")
        for k, sub in props.items():
            check_schema(sub, f"{path}.properties.{k}")
    if "items" in schema:
        check_schema(schema["items"], f"{path}.items")
    for kw in ("if", "then", "else"):
        if kw in schema:
            check_schema(schema[kw], f"{path}.{kw}")
    if "additionalProperties" in schema and schema["additionalProperties"] not in (True, False):
        raise SchemaError(f"{path}: unsupported additionalProperties value (only true or false)")


def validate(schema: dict, data: object, path: str = "") -> list[str]:
    """Return a list of `path: message` errors (empty when valid)."""
    if not isinstance(schema, dict):
        raise SchemaError("schema must be a JSON object")
    for kw in schema:
        if kw not in SUPPORTED and kw not in ANNOTATIONS:
            raise SchemaError(f"unsupported keyword: {kw}")
    here = path or "$"
    errors: list[str] = []

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(data, t) for t in types):
            errors.append(f"{here}: expected {' or '.join(types)}")
            return errors  # further checks would be noise
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{here}: {json.dumps(data)} not in enum {json.dumps(schema['enum'])}")
    if "pattern" in schema and isinstance(data, str) and not re.search(schema["pattern"], data):
        errors.append(f"{here}: {json.dumps(data)} does not match pattern {schema['pattern']}")
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{here}: {data} is below minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{here}: {data} is above maximum {schema['maximum']}")

    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{here}: missing required '{key}'")
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in data:
                errors.extend(validate(sub, data[key], _join(path, key)))
        if schema.get("additionalProperties") is False:
            for key in data:
                if key not in props:
                    errors.append(f"{here}: unexpected property '{key}'")
    if isinstance(data, list) and "items" in schema:
        for i, item in enumerate(data):
            errors.extend(validate(schema["items"], item, _join(path, i)))
    if "if" in schema:
        branch = "then" if not validate(schema["if"], data, path) else "else"
        if branch in schema:
            errors.extend(validate(schema[branch], data, path))
    return errors


def _load(p, what):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"cannot read {what} {p}: {e}", file=sys.stderr)
        raise SystemExit(2)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="check_json.py",
        description="Validate DATA.json against SCHEMA.json (JSON-Schema subset). "
                    "Exit 0 valid, 1 invalid, 2 usage/unsupported keyword/unreadable file.",
    )
    ap.add_argument("schema", help="schema JSON file")
    ap.add_argument("data", help="data JSON file to validate")
    args = ap.parse_args(argv)
    schema = _load(args.schema, "schema")
    data = _load(args.data, "data")
    try:
        check_schema(schema)
        errors = validate(schema, data)
    except SchemaError as e:
        print(str(e), file=sys.stderr)
        return 2
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
