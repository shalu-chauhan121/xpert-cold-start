"""Stage C synthetic contract/export tests. No dataset, evaluator or API calls."""
import ast
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import solution
import validation
from data import load_input
from validation import SchemaError, SchemaValidator, ValidationError, validate_output


def fixture():
    return {
        "people": [{"id": "P1", "circle": "staff", "looks_after": ["P2", "ME"],
                    "links": [{"organisation": "O1", "link": "supports"}]},
                   {"id": "P2", "circle": "child"}],
        "organisations": [{"id": "O1", "name": "Synthetic home", "type": "residence",
                           "side": "home", "role": "owner"}],
        "chats": [{"chat_id": "C1", "organisation": "O1"}, {"chat_id": "C2", "person": "P2"}],
        "goals": [{"title": "Walk daily नमस्ते বাংলা", "area": "health", "type": "habit",
                   "horizon": "3mo", "evidence": ["M1"]}],
        "open_loops": [
            {"title": "Prepare a draft", "type": "commitment", "owner": "ME", "chat_id": "C1",
             "source_msg": "M1", "status": "open", "due": None, "closed_by": None,
             "help": {"action": "assist", "next_step": "Draft a note", "needs_yes": False}},
            {"title": "Decide", "type": "question", "owner": "ME", "chat_id": "C1",
             "source_msg": "M1", "status": "open", "due": "2024-02-29",
             "help": {"action": "remind", "remind_at": "2026-11-05T10:00:00+05:30"}},
            {"title": "Wait", "type": "followup", "owner": "P1", "chat_id": "C1",
             "source_msg": "M1", "status": "open", "help": {"action": "leave", "reason": "In progress"}},
            {"title": "Delivered", "type": "deadline", "owner": "P2", "chat_id": "C1",
             "source_msg": "M1", "status": "done", "closed_by": "M2", "help": None},
            {"title": "Cancelled", "type": "commitment", "owner": "ME", "chat_id": "C1",
             "source_msg": "M1", "status": "dropped", "closed_by": "M3"}]
    }


class StageCFixture(unittest.TestCase):
    def setUp(self):
        self.folder = PROJECT / "tests" / ("stage-c-" + uuid.uuid4().hex)
        self.folder.mkdir()
        self.addCleanup(shutil.rmtree, self.folder)
        self.output = fixture()
        chats = [{"chat_id": "C1", "name": "Home", "is_group": True, "participants": ["ME", "P1"]},
                 {"chat_id": "C2", "name": "Child", "is_group": False, "participants": ["ME", "P2"]}]
        messages = [{"id": mid, "chat_id": cid, "sender_id": sender, "sender_name": sender,
                     "ts": ts, "body": body, "kind": "text", "quoted_id": quote}
                    for mid, cid, sender, ts, body, quote in (
                        ("M0", "C1", "ME", 50, "Earlier unrelated work", None),
                        ("M1", "C1", "ME", 100, "Walk daily; prepare a draft; decide; P1 is working; P2 owes a delivery", None),
                        ("M2", "C2", "P2", 200, "Delivery promised in M1 is complete", "M1"),
                        ("M3", "C1", "ME", 300, "Cancel the other task", "M1"))]
        self.write_inputs(chats, messages)
        self.data = load_input(self.folder)
        self.data.require_complete()
        self.validator = SchemaValidator()

    def write_inputs(self, chats, messages, seed=None):
        for name, rows in (("chats.jsonl", chats), ("messages.jsonl", messages)):
            (self.folder / name).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        (self.folder / "seed.json").write_text(json.dumps(seed or {}), encoding="utf-8")

    def invalid(self, path, schema=False):
        with self.assertRaises(ValidationError) as caught:
            if schema:
                self.validator.validate(self.output)
            else:
                validate_output(self.output, self.data, self.validator)
        self.assertIn(path, str(caught.exception))


class SchemaTests(StageCFixture):
    def test_all_five_categories_pass_actual_schema_and_semantics_without_mutation(self):
        before, evidence = copy.deepcopy(self.output), copy.deepcopy(self.data)
        self.validator.validate(self.output)
        validate_output(self.output, self.data)
        self.assertEqual(self.output, before)
        self.assertEqual(self.data, evidence)
        self.assertTrue(all(self.output.values()))

    def test_nullable_and_omitted_fields(self):
        for value in (None, "2024-02-29"):
            self.output["open_loops"][0]["due"] = value
            validate_output(self.output, self.data)
        for key in ("due", "closed_by"):
            self.output["open_loops"][0].pop(key, None)
        self.output["people"][0].pop("links")
        self.output["people"][0].pop("looks_after")
        validate_output(self.output, self.data)

    def test_every_required_field(self):
        # Walk the real schema and valid fixture, testing required keys at every
        # reachable object level (including link and help objects).
        def walk(node, schema, path):
            if isinstance(node, dict):
                for key in schema.get("required", []):
                    with self.subTest(path=path + "/" + key):
                        saved = node.pop(key)
                        try:
                            self.invalid(path + "/" + key, schema=True)
                        finally:
                            node[key] = saved
                for key, value in list(node.items()):
                    if key in schema.get("properties", {}):
                        walk(value, schema["properties"][key], path + "/" + key)
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    walk(item, schema["items"], path + "/" + str(i))
        walk(self.output, self.validator.schema, "")

    def test_wrong_primitive_types(self):
        for category, index, field, value in (("people", 0, "id", 1), ("organisations", 0, "name", False),
                                             ("chats", 0, "chat_id", None), ("goals", 0, "title", []),
                                             ("open_loops", 0, "due", 12)):
            with self.subTest(field=field):
                self.output = fixture()
                self.output[category][index][field] = value
                self.invalid("/%s/%s/%s" % (category, index, field), schema=True)
        for value in (0, 1, "false", None):
            self.output = fixture()
            self.output["open_loops"][0]["help"]["needs_yes"] = value
            self.invalid("/help/needs_yes", schema=True)

    def test_every_enum(self):
        def walk(node, schema, path):
            if isinstance(node, dict):
                for key, value in list(node.items()):
                    child = schema.get("properties", {}).get(key, {})
                    if "enum" in child:
                        with self.subTest(path=path + "/" + key):
                            node[key] = "__invalid_enum__"
                            try:
                                self.invalid(path + "/" + key, schema=True)
                            finally:
                                node[key] = value
                    walk(value, child, path + "/" + key)
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    walk(item, schema["items"], path + "/" + str(i))
        walk(self.output, self.validator.schema, "")

    def test_unknown_top_level_field(self):
        self.output["debug"] = {}
        self.invalid("/debug", schema=True)

    def test_unknown_fields_at_every_nested_object(self):
        nodes = [self.output[c][0] for c in self.output]
        nodes += [self.output["people"][0]["links"][0], self.output["open_loops"][0]["help"]]
        for node in nodes:
            with self.subTest(node=node):
                node["extra"] = True
                self.invalid("/extra", schema=True)
                del node["extra"]

    def test_array_structures_and_item_types(self):
        for category in self.output:
            for value in ({}, None, "array", [None], [[]]):
                with self.subTest(category=category, value=value):
                    original = self.output[category]
                    self.output[category] = value
                    self.invalid("/" + category, schema=True)
                    self.output[category] = original
        for path, node, key in (("/links", self.output["people"][0], "links"),
                                ("/looks_after", self.output["people"][0], "looks_after"),
                                ("/evidence", self.output["goals"][0], "evidence")):
            original = node[key]
            for value in ("bad", [42]):
                node[key] = value
                self.invalid(path, schema=True)
            node[key] = original

    def test_both_chat_targets(self):
        self.output["chats"][0]["person"] = "P1"
        self.invalid("oneOf", schema=True)

    def test_neither_chat_target(self):
        del self.output["chats"][0]["organisation"]
        self.invalid("oneOf", schema=True)

    def test_goal_limits_zero_ten_eleven(self):
        goal = self.output["goals"][0]
        for count in (0, 10):
            self.output["goals"] = [copy.deepcopy(goal) for _ in range(count)]
            validate_output(self.output, self.data)
        self.output["goals"].append(copy.deepcopy(goal))
        self.invalid("maxItems=10", schema=True)

    def test_empty_goal_evidence(self):
        self.output["goals"][0]["evidence"] = []
        self.invalid("minItems=1", schema=True)

    def test_non_json_values_are_rejected_before_serialization(self):
        for value in (float("nan"), float("inf"), ("P1",), {1: "value"}):
            self.output["people"] = value
            self.invalid("finite JSON", schema=True)


class SemanticTests(StageCFixture):
    def test_unknown_people_and_me_are_rejected(self):
        for identifier in ("ME", "fabricated"):
            self.output = fixture()
            self.output["people"][0]["id"] = identifier
            self.invalid("unknown or prohibited input ID " + identifier)

    def test_missing_people_and_chats_including_silent_people(self):
        for category in ("people", "chats"):
            self.output = fixture()
            self.output[category].pop()
            self.invalid("/" + category + ": missing required input ID")

    def test_duplicate_record_ids(self):
        for category in ("people", "organisations", "chats"):
            self.output = fixture()
            self.output[category].append(copy.deepcopy(self.output[category][0]))
            self.invalid("duplicate ID")

    def test_blank_organisation_id(self):
        self.output["organisations"][0]["id"] = " "
        self.invalid("ID must not be blank")

    def test_unknown_chat_record_and_loop_chat(self):
        self.output["chats"][0]["chat_id"] = "invented"
        self.invalid("unknown or prohibited input ID invented")
        self.output = fixture()
        self.output["open_loops"][0]["chat_id"] = "invented"
        self.invalid("/open_loops/0/chat_id: unknown chat")

    def test_unknown_targets_and_organisation_links(self):
        for category, index, key in (("chats", 0, "organisation"), ("chats", 1, "person")):
            self.output = fixture()
            self.output[category][index][key] = "invented"
            self.invalid("/chats/%d/%s: unknown" % (index, key))
        self.output = fixture()
        self.output["people"][0]["links"][0]["organisation"] = "invented"
        self.invalid("/links/0/organisation: unknown")

    def test_care_references_unknown_and_self(self):
        for identifier in ("invented", "P1"):
            self.output["people"][0]["looks_after"] = [identifier]
            self.invalid("/looks_after/0")

    def test_unknown_goal_evidence(self):
        self.output["goals"][0]["evidence"] = ["M1", "fabricated"]
        self.invalid("/goals/0/evidence/1: unknown evidence")

    def test_unknown_or_missing_loop_evidence(self):
        for value in ("", "fabricated"):
            self.output["open_loops"][0]["source_msg"] = value
            self.invalid("/source_msg: unknown evidence")
        del self.output["open_loops"][0]["source_msg"]
        self.invalid("/source_msg: required")

    def test_source_must_belong_to_origin_chat(self):
        self.output["open_loops"][0]["source_msg"] = "M2"
        self.invalid("source message must belong")

    def test_impossible_owner_references(self):
        for owner in ("", "invented", "O1", "C1"):
            self.output["open_loops"][0]["owner"] = owner
            self.invalid("/owner: unknown person")

    def test_owner_need_not_be_sender_or_source_chat_participant(self):
        # P2 is explicitly named in M1 but is only a participant of C2.
        self.output["open_loops"][0]["owner"] = "P2"
        validate_output(self.output, self.data)

    def test_closed_loops_require_existing_closure_and_no_help(self):
        for status in ("done", "dropped"):
            for closure in (None, "fabricated"):
                self.output = fixture()
                self.output["open_loops"][3].update(status=status, closed_by=closure)
                self.invalid("/closed_by")
            for help_value in ({"action": "leave", "reason": "No"}, {"action": "assist"}):
                self.output = fixture()
                self.output["open_loops"][3].update(status=status, help=help_value)
                self.invalid("cannot contain a help recommendation")

    def test_closure_cannot_predate_origin(self):
        self.output["open_loops"][3]["closed_by"] = "M0"
        self.invalid("closure evidence predates")

    def test_cross_chat_closure_and_equal_timestamp_allowed(self):
        validate_output(self.output, self.data)
        self.data.messages_by_id["M2"].timestamp = self.data.messages_by_id["M1"].timestamp
        validate_output(self.output, self.data)

    def test_open_loop_has_no_stale_closure(self):
        self.output["open_loops"][0]["closed_by"] = "M2"
        self.invalid("open/reopened loop cannot")

    def test_open_loop_requires_help(self):
        for remove in (False, True):
            self.output["open_loops"][0]["help"] = None
            if remove:
                del self.output["open_loops"][0]["help"]
            self.invalid("open loop requires a help decision")

    def test_missing_action_specific_fields(self):
        for index, field in ((0, "next_step"), (0, "needs_yes"), (1, "remind_at"), (2, "reason")):
            self.output = fixture()
            del self.output["open_loops"][index]["help"][field]
            self.invalid("/help/" + field)

    def test_blank_action_fields(self):
        for index, field in ((0, "next_step"), (1, "remind_at"), (2, "reason")):
            self.output = fixture()
            self.output["open_loops"][index]["help"][field] = " "
            self.invalid("/help/" + field)

    def test_invalid_calendar_dates(self):
        for value in ("2023-02-29", "2026-13-01", "2026-04-31", "0000-01-01", "20261105",
                      "2026-1-01", "tomorrow", "2026-11-05T00:00:00Z"):
            with self.subTest(value=value):
                self.output["open_loops"][0]["due"] = value
                self.invalid("invalid calendar date")

    def test_invalid_timestamps_and_offsets(self):
        for value in ("2026-11-05", "2026-11-05T10:00:00", "2026-02-30T10:00:00Z",
                      "2026-11-05T24:00:00Z", "2026-11-05T10:00:60Z", "2026-11-05T10:00:00+24:00",
                      "2026-11-05T10:00:00+05:99", "tomorrow", "20261105T100000Z"):
            with self.subTest(value=value):
                self.output["open_loops"][1]["help"]["remind_at"] = value
                self.invalid("invalid timestamp")

    def test_reminder_relative_to_as_of_not_wall_clock(self):
        for value in ("1970-01-01T00:04:59Z", "1970-01-01T00:05:00Z"):
            self.output["open_loops"][1]["help"]["remind_at"] = value
            self.invalid("reminder must be after input as_of")
        self.output["open_loops"][1]["help"]["remind_at"] = "1970-01-01T00:05:00.000001Z"
        validate_output(self.output, self.data)

    def test_incomplete_input_timestamp_cannot_be_exported(self):
        path = self.folder / "messages.jsonl"
        path.write_text(path.read_text().replace('"ts": 100', '"ts": null'), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Input loading is incomplete"):
            validate_output(self.output, load_input(self.folder))


class BackendTests(StageCFixture):
    def schema_file(self, schema):
        path = self.folder / "schema.json"
        path.write_text(json.dumps(schema), encoding="utf-8")
        return path

    def test_backend_identity_and_actual_schema_loaded(self):
        self.assertEqual((validation.BACKEND, validation.BACKEND_VERSION), ("xpert-scoped-schema", "1.0.0"))
        with validation.SCHEMA_PATH.open(encoding="utf-8") as stream:
            self.assertEqual(self.validator.schema, json.load(stream))
        changed = copy.deepcopy(self.validator.schema)
        changed["properties"]["goals"]["maxItems"] = 0
        with self.assertRaisesRegex(ValidationError, "maxItems=0"):
            SchemaValidator(self.schema_file(changed)).validate(self.output)

    def test_unsupported_keywords_fail_even_in_unused_branches(self):
        for keyword, value in (("$ref", "https://example.invalid/schema"), ("format", "date"),
                               ("pattern", ".*"), ("anyOf", []), ("unevaluatedProperties", False),
                               ("minimum", 0), ("$defs", {})):
            schema = copy.deepcopy(self.validator.schema)
            schema["properties"]["unused"] = {keyword: value}
            with self.subTest(keyword=keyword), self.assertRaisesRegex(SchemaError, "unsupported schema keyword"):
                SchemaValidator(self.schema_file(schema))

    def test_invalid_schema_configuration_fails(self):
        for schema in ({"type": "invented"}, {"type": ["string", "string"]}, {"required": [1]},
                       {"properties": []}, {"items": []}, {"oneOf": []}, {"maxItems": True},
                       {"additionalProperties": {}}, {"enum": []}, {"$schema": "old-draft"}, False):
            with self.subTest(schema=schema), self.assertRaises(SchemaError):
                SchemaValidator(self.schema_file(schema))

    def test_missing_or_corrupt_schema_has_no_fallback(self):
        path = self.folder / "missing.json"
        with self.assertRaises(SchemaError):
            SchemaValidator(path)
        for raw in ('{broken', '{"type":"array","type":"object"}'):
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(SchemaError):
                SchemaValidator(path)

    def test_type_enum_and_nullable_rules_independent_of_project_shape(self):
        cases = [({"type": "boolean"}, [True, False], [0, 1, None]),
                 ({"type": "integer"}, [1, 1.0], [True, 1.5]),
                 ({"type": "number"}, [1, 0.5], [False, "1"]),
                 ({"enum": [1]}, [1, 1.0], [True, False]),
                 ({"type": ["object", "null"], "required": ["a"]}, [None, {"a": 1}], [{}, []]),
                 ({"type": "array", "minItems": 1, "maxItems": 2, "items": {"type": "string"}},
                  [["a"], ["a", "b"]], [[], [1], ["a", "b", "c"]])]
        for schema, valid, invalid in cases:
            validator = SchemaValidator(self.schema_file(schema))
            for value in valid:
                validator.validate(value)
            for value in invalid:
                with self.subTest(schema=schema, value=value), self.assertRaises(ValidationError):
                    validator.validate(value)

    def test_backend_runs_without_site_packages_or_network_in_fresh_process(self):
        path = self.folder / "candidate.json"
        path.write_text(json.dumps(self.output), encoding="utf-8")
        script = '''
import builtins, json, socket, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'jsonschema', 'referencing', 'rpds', 'attrs'}:
        raise AssertionError('External backend import attempted')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
def deny(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo'}:
        raise AssertionError('Network attempted')
sys.addaudithook(deny)
try:
    socket.getaddrinfo('example.invalid', 443)
except AssertionError:
    pass
else:
    raise AssertionError('Network guard ineffective')
from validation import validate_output, BACKEND, BACKEND_VERSION
from data import load_input
with open(sys.argv[2], encoding='utf-8') as stream:
    validate_output(json.load(stream), load_input(sys.argv[1]))
print(BACKEND, BACKEND_VERSION)
'''
        result = subprocess.run([sys.executable, "-B", "-S", "-c", script, str(self.folder), str(path)],
                                cwd=PROJECT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "xpert-scoped-schema 1.0.0")

    def test_runtime_sources_parse_as_python39(self):
        for name in ("solution.py", "validation.py"):
            ast.parse((PROJECT / name).read_text(encoding="utf-8"), feature_version=(3, 9))

    def test_selected_backend_import_failure_is_not_hidden(self):
        script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'validation':
        raise ModuleNotFoundError('selected backend unavailable')
    if name in {'jsonschema', 'referencing'}:
        raise AssertionError('fallback attempted')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import solution
'''
        result = subprocess.run([sys.executable, "-B", "-S", "-c", script], cwd=PROJECT,
                                capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ModuleNotFoundError: selected backend unavailable", result.stderr)
        self.assertNotIn("fallback attempted", result.stderr)


class ExportTests(StageCFixture):
    def setUp(self):
        super().setUp()
        self.destination = self.folder / "output.json"
        self.old = json.dumps(self.output, ensure_ascii=False).encode("utf-8")
        self.destination.write_bytes(self.old)

    def assert_preserved(self):
        self.assertEqual(self.destination.read_bytes(), self.old)
        self.assertEqual(list(self.folder.glob(".output.json.*.tmp")), [])

    def test_success_exposes_only_complete_valid_json_at_replace(self):
        original = os.replace
        replacements = []
        def inspect(source, destination):
            self.assertEqual(self.destination.read_bytes(), self.old)
            self.assertEqual(source.parent, self.destination.parent)
            with source.open(encoding="utf-8") as stream:
                candidate = json.load(stream)
            validate_output(candidate, self.data)
            self.assertEqual(candidate, self.output)
            replacements.append(destination)
            original(source, destination)
        with patch.object(solution.os, "replace", inspect):
            solution.export_output(self.output, self.data, self.destination)
        self.assertEqual(replacements, [self.destination])
        self.assertEqual(json.loads(self.destination.read_text(encoding="utf-8")), self.output)
        self.assertEqual(list(self.folder.glob(".output.json.*.tmp")), [])

    def test_validation_failure_creates_no_temporary(self):
        self.output["people"] = []
        with patch.object(solution.json, "dump") as dump, patch.object(solution.os, "replace") as replace:
            with self.assertRaises(ValidationError):
                solution.export_output(self.output, self.data, self.destination)
            dump.assert_not_called()
            replace.assert_not_called()
        self.assert_preserved()

    def test_partial_write_error_and_keyboard_interrupt_preserve_old_bytes(self):
        for error in (OSError("disk full"), KeyboardInterrupt()):
            def broken(value, stream, **kwargs):
                stream.write('{"people": [')
                stream.flush()
                self.assertEqual(self.destination.read_bytes(), self.old)
                raise error
            with patch.object(solution.json, "dump", broken), self.assertRaises(type(error)):
                solution.export_output(self.output, self.data, self.destination)
            self.assert_preserved()

    def test_write_failure_without_old_destination_exposes_no_final_file(self):
        self.destination.unlink()
        def broken(value, stream, **kwargs):
            stream.write('{"people": [')
            stream.flush()
            self.assertFalse(self.destination.exists())
            raise OSError("interrupted")
        with patch.object(solution.json, "dump", broken), self.assertRaises(OSError):
            solution.export_output(self.output, self.data, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.folder.glob(".output.json.*.tmp")), [])

    def test_failed_flush_or_close_preserves_old_bytes(self):
        original_open = Path.open
        for fail_at in ("flush", "close"):
            class Stream:
                def __init__(inner, stream):
                    inner.stream = stream
                def __enter__(inner):
                    return inner
                def __exit__(inner, *args):
                    inner.stream.close()
                    if fail_at == "close":
                        raise OSError("close failed")
                def write(inner, value):
                    return inner.stream.write(value)
                def flush(inner):
                    if fail_at == "flush":
                        raise OSError("flush failed")
                    return inner.stream.flush()
                def fileno(inner):
                    return inner.stream.fileno()
            def opened(path, *args, **kwargs):
                stream = original_open(path, *args, **kwargs)
                return Stream(stream) if args and args[0] == "x" else stream
            with patch.object(Path, "open", opened), self.assertRaises(OSError):
                solution.export_output(self.output, self.data, self.destination)
            self.assert_preserved()

    def test_failed_fsync_preserves_old_bytes(self):
        with patch.object(solution.os, "fsync", side_effect=OSError("sync failed")), self.assertRaises(OSError):
            solution.export_output(self.output, self.data, self.destination)
        self.assert_preserved()

    def test_failed_replace_preserves_old_bytes(self):
        with patch.object(solution.os, "replace", side_effect=OSError("replace failed")), self.assertRaises(OSError):
            solution.export_output(self.output, self.data, self.destination)
        self.assert_preserved()

    def test_invalid_or_changed_serialized_output_never_replaces(self):
        for text in ('{broken', '{"people":[]}', '{"people":[],"people":[]}',
                     json.dumps(dict(self.output, goals=[]))):
            def corrupt(value, stream, **kwargs):
                stream.write(text)
            with patch.object(solution.json, "dump", corrupt), self.assertRaises(ValueError):
                solution.export_output(self.output, self.data, self.destination)
            self.assert_preserved()

    def test_temp_creation_collision_never_deletes_unowned_file(self):
        token = uuid.UUID(int=1)
        collision = self.folder / (".output.json." + token.hex + ".tmp")
        collision.write_bytes(b"owned by another writer")
        with patch.object(solution.uuid, "uuid4", return_value=token), self.assertRaises(FileExistsError):
            solution.export_output(self.output, self.data, self.destination)
        self.assertEqual(collision.read_bytes(), b"owned by another writer")
        self.assertEqual(self.destination.read_bytes(), self.old)

    def test_main_integrates_validation_and_returns_nonzero_on_invalid_output(self):
        self.output["goals"][0]["evidence"] = ["invented"]
        with patch.object(solution, "assemble_output", return_value=self.output), patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(solution.main(self.folder, self.destination), 1)
            self.assertIn("unknown evidence", err.getvalue())
        self.assert_preserved()

    def test_main_success_with_synthetic_completed_results(self):
        with patch.object(solution, "assemble_output", return_value=self.output):
            self.assertEqual(solution.main(self.folder, self.destination), 0)
        self.assertEqual(json.loads(self.destination.read_text(encoding="utf-8")), self.output)

    def test_main_write_failure_returns_nonzero_and_preserves_destination(self):
        with patch.object(solution, "assemble_output", return_value=self.output), \
                patch.object(solution.os, "replace", side_effect=OSError("replace failed")), \
                patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(solution.main(self.folder, self.destination), 1)
            self.assertIn("replace failed", err.getvalue())
        self.assert_preserved()

    def test_missing_selected_schema_blocks_publication(self):
        with patch.object(solution, "SchemaValidator", side_effect=SchemaError("missing schema")), \
                self.assertRaises(SchemaError):
            solution.export_output(self.output, self.data, self.destination)
        self.assert_preserved()

    def test_successful_first_publication(self):
        self.destination.unlink()
        solution.export_output(self.output, self.data, self.destination)
        self.assertEqual(json.loads(self.destination.read_text(encoding="utf-8")), self.output)
        self.assertEqual(list(self.folder.glob(".output.json.*.tmp")), [])

    def test_cli_fails_for_missing_configuration_or_incomplete_input(self):
        for missing_seed in (False, True):
            if missing_seed:
                (self.folder / "seed.json").unlink()
            result = subprocess.run([sys.executable, "-B", str(PROJECT / "solution.py"),
                                     str(self.folder), str(self.destination)], capture_output=True, text=True, timeout=30,
                                    env={k: v for k, v in os.environ.items() if not k.startswith("LLM_")})
            self.assertEqual(result.returncode, 1)
            self.assertIn("Input loading is failed" if missing_seed else "configuration", result.stderr)
            self.assert_preserved()

    def test_truly_empty_cli_succeeds_but_seed_only_is_not_empty_inference(self):
        self.write_inputs([], [])
        result = subprocess.run([sys.executable, "-B", str(PROJECT / "solution.py"), str(self.folder), str(self.destination)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.destination.read_text()), {key: [] for key in self.output})
        self.write_inputs([], [], {"goals": [{"title": "Requires review"}]})
        with patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(solution.main(self.folder, self.destination), 1)

    def test_cli_requires_exactly_two_arguments(self):
        result = subprocess.run([sys.executable, "-B", str(PROJECT / "solution.py")],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
