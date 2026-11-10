"""Stage C: supplied schema vocabulary and evidence integrity, offline.

Backend: xpert-scoped-schema 1.0.0 (stdlib, Python >=3.9). Not a general Draft
2020-12 implementation. Unsupported keywords fail closed; no network resolver
or backend fallback. Reference validity does not establish textual entailment.
"""
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path

BACKEND = "xpert-scoped-schema"
BACKEND_VERSION = "1.0.0"
SCHEMA_PATH = Path(__file__).resolve().with_name("schema.json")
DIALECT = "https://json-schema.org/draft/2020-12/schema"
KEYWORDS = {"type", "enum", "required", "properties", "additionalProperties",
            "items", "minItems", "maxItems", "oneOf", "$schema", "title", "description"}
TYPES = {"object", "array", "string", "boolean", "null", "integer", "number"}


class ValidationError(ValueError):
    def __init__(self, errors):
        self.errors = tuple(errors)
        super().__init__("Output validation failed:\n" + "\n".join(self.errors))


class SchemaError(ValueError):
    """Missing, malformed, or unsupported schema configuration."""


def _path(parent, key):
    return parent + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def _constant(value):
    raise ValueError("Non-finite JSON number: " + value)


def read_json(stream):
    text = stream.read()
    try:
        return json.loads(text, object_pairs_hook=_unique_object, parse_constant=_constant)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        candidate = _outermost_object(text)
        if candidate is None:
            raise
        return json.loads(candidate, object_pairs_hook=_unique_object, parse_constant=_constant)


def _outermost_object(text):
    """Recover the outermost JSON object from fenced or prose-wrapped output.

    Session-08 retry evidence: four finish-stop responses (pilot_hi goals,
    three task-review jobs) failed strict JSON-object parsing under
    response_format json_object; response bodies are not retained, so the
    exact wrapping is unknown. This fallback only unwraps markdown fences or
    surrounding prose around ONE balanced {...}; the slice is then parsed
    with the same strict rules (duplicate keys, non-finite constants and
    non-object payloads still fail, and no validators are loosened). Values
    are never extracted with eval or regex coercion.
    """
    depth = 0
    start = None
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if start is None:
            if char != "{":
                continue
            start = index
            depth = 1
        elif in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if not depth:
                return text[start:index + 1]
    return None


def _check_schema(schema, path=""):
    def fail(reason):
        raise SchemaError((path or "/") + ": " + reason)
    if not isinstance(schema, dict):
        fail("this backend supports object schemas only")
    unknown = set(schema) - KEYWORDS
    if unknown:
        fail("unsupported schema keyword(s): " + ", ".join(sorted(unknown)))
    if "$schema" in schema and schema["$schema"] != DIALECT:
        fail("unsupported schema dialect")
    for key in ("title", "description"):
        if key in schema and not isinstance(schema[key], str):
            fail(key + " must be a string")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if (not types or any(not isinstance(t, str) or t not in TYPES for t in types)
                or len(types) != len(set(types))):
            fail("invalid type declaration")
    if "enum" in schema and (not isinstance(schema["enum"], list) or not schema["enum"]):
        fail("enum must be a nonempty array")
    if "required" in schema:
        required = schema["required"]
        if (not isinstance(required, list) or any(not isinstance(k, str) for k in required)
                or len(required) != len(set(required))):
            fail("required must be an array of unique strings")
    if "additionalProperties" in schema and type(schema["additionalProperties"]) is not bool:
        fail("only boolean additionalProperties is supported")
    for key in ("minItems", "maxItems"):
        if key in schema and (type(schema[key]) is not int or schema[key] < 0):
            fail(key + " must be a nonnegative integer")
    if "properties" in schema:
        if not isinstance(schema["properties"], dict):
            fail("properties must be an object")
        for key, child in schema["properties"].items():
            _check_schema(child, _path(_path(path, "properties"), key))
    if "items" in schema:
        _check_schema(schema["items"], _path(path, "items"))
    if "oneOf" in schema:
        if not isinstance(schema["oneOf"], list) or not schema["oneOf"]:
            fail("oneOf must be a nonempty array")
        for i, child in enumerate(schema["oneOf"]):
            _check_schema(child, _path(_path(path, "oneOf"), i))


def _json_errors(value, path=""):
    if value is None or type(value) in (str, bool, int):
        return []
    if type(value) is float and math.isfinite(value):
        return []
    if type(value) is list:
        return [e for i, child in enumerate(value) for e in _json_errors(child, _path(path, i))]
    if type(value) is dict and all(type(key) is str for key in value):
        return [e for key, child in value.items() for e in _json_errors(child, _path(path, key))]
    return [(path or "/") + ": expected a finite JSON value with string object keys"]


def _matches_type(value, name):
    return {"object": type(value) is dict, "array": type(value) is list,
            "string": type(value) is str, "boolean": type(value) is bool,
            "null": value is None, "number": type(value) in (int, float),
            "integer": type(value) is int or type(value) is float and value.is_integer()}[name]


def _equal(left, right):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_equal(left[k], right[k]) for k in left)
    return left == right


def _schema_errors(value, schema, path=""):
    errors = []
    here = path or "/"
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_matches_type(value, t) for t in types):
            return [here + ": expected type " + " or ".join(types)]
    if "enum" in schema and not any(_equal(value, item) for item in schema["enum"]):
        errors.append(here + ": expected one of " + repr(schema["enum"]))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(_path(path, key) + ": required field is missing")
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                errors.extend(_schema_errors(child, properties[key], _path(path, key)))
            elif schema.get("additionalProperties") is False:
                errors.append(_path(path, key) + ": unknown field (additionalProperties=false)")
    if isinstance(value, list):
        for key, failed in (("minItems", len(value) < schema.get("minItems", 0)),
                            ("maxItems", len(value) > schema.get("maxItems", len(value)))):
            if failed:
                errors.append(here + ": " + key + "=" + str(schema[key]) + " violated")
        if "items" in schema:
            for i, child in enumerate(value):
                errors.extend(_schema_errors(child, schema["items"], _path(path, i)))
    if "oneOf" in schema:
        matches = sum(not _schema_errors(value, branch, path) for branch in schema["oneOf"])
        if matches != 1:
            errors.append(here + ": oneOf requires exactly one matching branch; got " + str(matches))
    return errors


class SchemaValidator:
    """Read the actual local schema; never resolve URLs or select a backend."""
    def __init__(self, schema_path=SCHEMA_PATH):
        try:
            with Path(schema_path).open(encoding="utf-8") as stream:
                self.schema = read_json(stream)
        except (OSError, ValueError) as error:
            raise SchemaError("Cannot load local schema: " + str(error)) from error
        _check_schema(self.schema)

    def validate(self, output):
        errors = _json_errors(output)
        if not errors:
            errors = _schema_errors(output, self.schema)
        if errors:
            raise ValidationError(errors)


def _date(value):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("expected YYYY-MM-DD")
    return date.fromisoformat(value)


def _instant(value):
    # Never assume a local zone; interpretation of relative dates is deferred.
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                        r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})", value):
        raise ValueError("expected ISO date-time with seconds and explicit Z or UTC offset")
    if value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise ValueError("invalid UTC offset")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def validate_output(output, data, validator=None):
    """Check complete input, output coverage, references, chronology and help.

    Third-party ownership and cross-chat closure are permitted. Later reasoning
    must establish textual support; this layer must not guess it from senders,
    participant overlap, or message IDs. No values are repaired or invented.
    """
    data.require_complete()
    (validator if validator is not None else SchemaValidator()).validate(output)
    errors = []

    def fail(path, reason):
        errors.append(path + ": " + reason)

    def records(category, key):
        result = {}
        for i, item in enumerate(output[category]):
            identifier = item[key]
            if not identifier.strip():
                fail("/%s/%d/%s" % (category, i, key), "ID must not be blank")
            if identifier in result:
                fail("/%s/%d/%s" % (category, i, key), "duplicate ID " + identifier)
            result[identifier] = item
        return result

    people = records("people", "id")
    organisations = records("organisations", "id")
    chats = records("chats", "chat_id")
    for category, actual, expected in (("people", set(people), set(data.person_ids)),
                                       ("chats", set(chats), set(data.chats_by_id))):
        for identifier in sorted(expected - actual):
            fail("/" + category, "missing required input ID " + identifier)
        for identifier in sorted(actual - expected):
            fail("/" + category, "unknown or prohibited input ID " + identifier)

    def person(identifier, path, allow_me=False):
        if not (allow_me and identifier == "ME") and identifier not in people:
            fail(path, "unknown person reference " + identifier)

    def organisation(identifier, path):
        if identifier not in organisations:
            fail(path, "unknown organisation reference " + identifier)

    def evidence(identifier, path):
        record = data.messages_by_id.get(identifier)
        if record is None:
            fail(path, "unknown evidence message ID " + identifier)
        return record

    for i, item in enumerate(output["people"]):
        for j, link in enumerate(item.get("links", [])):
            organisation(link["organisation"], "/people/%d/links/%d/organisation" % (i, j))
        for j, identifier in enumerate(item.get("looks_after", [])):
            person(identifier, "/people/%d/looks_after/%d" % (i, j), allow_me=True)
            if identifier == item["id"]:
                fail("/people/%d/looks_after/%d" % (i, j), "self-care is not a care relationship")
    for i, item in enumerate(output["chats"]):
        if "person" in item:
            person(item["person"], "/chats/%d/person" % i)
        else:
            organisation(item["organisation"], "/chats/%d/organisation" % i)
    for i, item in enumerate(output["goals"]):
        for j, identifier in enumerate(item["evidence"]):
            evidence(identifier, "/goals/%d/evidence/%d" % (i, j))
    for i, item in enumerate(output["open_loops"]):
        path = "/open_loops/%d" % i
        person(item["owner"], path + "/owner", allow_me=True)
        if item["chat_id"] not in chats:
            fail(path + "/chat_id", "unknown chat reference " + item["chat_id"])
        source = evidence(item["source_msg"], path + "/source_msg")
        if source and source.original["chat_id"] != item["chat_id"]:
            fail(path + "/source_msg", "source message must belong to the declared origin chat")
        closed = item.get("closed_by")
        if item["status"] == "open":
            if closed is not None:
                fail(path + "/closed_by", "open/reopened loop cannot have current closure evidence")
            help_value = item.get("help")
            if help_value is None:
                fail(path + "/help", "open loop requires a help decision")
            else:
                action = help_value["action"]
                fields = {"assist": ("next_step", "needs_yes"), "remind": ("remind_at",),
                          "leave": ("reason",)}[action]
                for field in fields:
                    if field not in help_value or (isinstance(help_value[field], str)
                                                   and not help_value[field].strip()):
                        fail(path + "/help/" + field, action + " requires a nonempty " + field)
        else:
            if closed is None:
                fail(path + "/closed_by", "done/dropped loop requires closure evidence")
            if item.get("help") is not None:
                fail(path + "/help", "done/dropped loop cannot contain a help recommendation")
        if closed is not None:
            closure = evidence(closed, path + "/closed_by")
            if source and closure and closure.timestamp < source.timestamp:
                fail(path + "/closed_by", "closure evidence predates the source obligation")
        if item.get("due") is not None:
            try:
                _date(item["due"])
            except ValueError as error:
                fail(path + "/due", "invalid calendar date: " + str(error))
        help_value = item.get("help") or {}
        if "remind_at" in help_value:
            try:
                instant = _instant(help_value["remind_at"])
                seconds = (instant - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()
                if data.as_of is None or seconds <= data.as_of:
                    fail(path + "/help/remind_at", "reminder must be after input as_of")
            except (ValueError, OverflowError) as error:
                fail(path + "/help/remind_at", "invalid timestamp: " + str(error))
    if errors:
        raise ValidationError(errors)
