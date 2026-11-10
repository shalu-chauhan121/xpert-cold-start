"""Session-11 regressions for the two packet-contract enumeration gaps.

Session 10 live evidence (`session-10-gate-6-validated-{evidence,captures}.json`,
SHA-256 42CB1DC7…/823A8EC9…) showed two fail-closed validation failures with
valid JSON whose field enumerations were never disclosed in the packet
contracts:
- Issue A: the organisations packet contract said `record:{name,type,side,role}`
  without the permitted values; the model answered type="organisation",
  side=null, role=null and the schema (schema.json, backed by check.py's
  ORG_TYPES/ORG_ROLES) rejected all three.
- Issue B: the task-review packet contract required `details.type` without
  naming the permitted values; the model answered "task"/"request"; the
  schema wants commitment/followup/deadline/question.

Repairs: contract TEXT enumerations + version bumps (context-4→context-5 for
the semantic-seam banner, task-review-3→task-review-4) only. No parser or
validator was touched; unsupported values still fail closed exactly as
before, with a valid-permitted-value success control next to every
rejection so nothing is tuned to the captured responses.
"""
import ast
import json
import re
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "tests"))

from reasoning import resolve_organisations, CONTEXT_VERSION, CONTEXT_PROMPT
from tasks import validate_event, TaskError
from validation import SchemaValidator, SCHEMA_PATH, ValidationError
from test_reasoning import fixture, FakeClient
from test_reasoning_resolution import extracted, obs


def _source(name):
    return (PROJECT / name).read_text(encoding="utf-8")


def _org_contract_text():
    """The contract string inside resolve_organisations, from source.

    The source expression is a parenthesized run of implicit string
    literals; literal evaluation yields the exact text the model sees and
    avoids any quote/newline artifacts from raw source matching.
    """
    match = re.search(r"contract = (\(.*?same-entity decisions\.'\))",
                      _source("reasoning.py"), re.DOTALL)
    assert match is not None, "organisation contract not found in source"
    # The source is trusted input written by this project's own reviews.
    return " ".join(ast.literal_eval(match.group(1)).split())


def _task_contract_text():
    match = re.search(r'"contract": \'(.*?)Other details are empty\.\'',
                      _source("tasks.py"), re.DOTALL)
    assert match is not None, "task-review contract not found in source"
    return (" ".join(match.group(1).split())
            + " Other details are empty.")


def _schema_enums():
    """The authoritative runtime schema, the same one the validator enforces."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    org = schema["properties"]["organisations"]["items"]["properties"]
    task_type = schema["properties"]["open_loops"]["items"]["properties"]["type"]
    return {"org_type": org["type"]["enum"],
            "org_side": org["side"]["enum"],
            "org_role": org["role"]["enum"],
            "task_type": task_type["enum"]}


def _org_extraction():
    span = {"message_id": "M0", "start": 0, "end": 10, "text": "Lease copy"}
    candidate = dict(obs("organisation", "o1"), windows=["w"],
                     meaning="HomeServe was contacted about repairs",
                     evidence=[span])
    return extracted([candidate])


def _org_reply(record):
    return {"groups": [{"members": ["o1"], "record": record, "aliases": []}],
            "rejected": [], "pending": []}


def _org_output_shell(record, invalid):
    return {"people": [], "organisations": [record], "chats": [],
            "goals": [], "open_loops": []}


class OrganisationContractDocumentationTests(unittest.TestCase):
    """Issue A: every permitted value is stated; nothing invented or omitted."""

    def test_every_schema_value_is_documented(self):
        enums = _schema_enums()
        contract = _org_contract_text()
        for key in ("org_type", "org_side", "org_role"):
            for value in enums[key]:
                self.assertIn(value, contract, key + " missing " + value)

    def test_documented_lists_equal_the_schema_exactly(self):
        enums = _schema_enums()
        contract = _org_contract_text()
        for key in ("org_type", "org_side", "org_role"):
            # The verbatim comma-joined enum appears; broader or different
            # lists would break this join.
            self.assertIn(", ".join(enums[key]), contract)

    def test_no_unlisted_substitution_guidance(self):
        contract = _org_contract_text()
        self.assertIn("record.type is exactly one of", contract)
        self.assertIn("record.side is one of", contract)
        self.assertIn("record.role is one of", contract)
        self.assertIn("Never substitute an unlisted value or null", contract)


class TaskContractDocumentationTests(unittest.TestCase):
    """Issue B: every permitted details.type is stated, nothing invented."""

    def test_every_schema_value_is_documented(self):
        contract = _task_contract_text()
        for value in _schema_enums()["task_type"]:
            self.assertIn(value, contract, "missing type value " + value)
        self.assertIn("type is exactly one of", contract)
        self.assertIn("never substitute or invent another value", contract)

    def test_documented_list_equals_the_schema_exactly(self):
        self.assertIn(", ".join(_schema_enums()["task_type"]),
                      _task_contract_text())


class OrganisationContractBehaviourTests(unittest.TestCase):
    """Valid permitted types still succeed; unsupported values fail closed."""

    def setUp(self):
        self.data, self.plan = fixture()

    def _run(self, record):
        return resolve_organisations(self.data, _org_extraction(),
                                     FakeClient([_org_reply(record)]))

    def test_legitimate_company_type_is_accepted(self):
        result = self._run({"name": "HomeServe", "type": "company",
                            "side": "work", "role": "partner"})
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(result["items"][0]["type"], "company")
        self.assertEqual(result["pending"], [])

    def test_legitimate_other_type_is_accepted(self):
        # Anti-overfit control on a SECOND permitted value: the contract
        # documents the whole enumeration, not one captured-word fix.
        result = self._run({"name": "HomeServe", "type": "other",
                            "side": "home", "role": "helper"})
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(result["items"][0]["type"], "other")

    def test_captured_style_unsupported_values_fail_closed(self):
        result = self._run({"name": "HomeServe", "type": "organisation",
                            "side": None, "role": None})
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["items"], [])
        self.assertEqual(result["failures"], ["organisation_resolution_failed"])

    def test_generic_unsupported_type_fails_closed(self):
        result = self._run({"name": "HomeServe", "type": "agency",
                            "side": "work", "role": "owner"})
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["items"], [])

    def test_schema_enums_unchanged_by_this_repair(self):
        """The real schema still accepts permitted values and rejects the rest."""
        validator = SchemaValidator()
        record = {"id": "temporary", "name": "x", "type": "company",
                  "side": "home", "role": "other"}
        for field, allowed in (("type", _schema_enums()["org_type"]),
                               ("side", _schema_enums()["org_side"]),
                               ("role", _schema_enums()["org_role"])):
            validator.validate({"people": [], "organisations": [dict(
                record, **{field: allowed[-1]})], "chats": [],
                "goals": [], "open_loops": []})
            for bad in (None, allowed[0] + "-unlisted"):
                with self.assertRaises(ValidationError):
                    validator.validate({"people": [], "organisations": [dict(
                        record, **{field: bad})], "chats": [], "goals": [],
                        "open_loops": []})


class TaskContractBehaviourTests(unittest.TestCase):
    """Valid details.type accepted; invented values and hash-evidence fail."""

    def setUp(self):
        self.data, self.plan = fixture()
        self.observation = dict(obs("task_create", "t1"), windows=["w"],
                                meaning="Records must be shared tomorrow",
                                evidence=[self._span()])

    def _span(self):
        from dataclasses import asdict
        body = self.data.messages_by_id["M0"].original["body"]
        span = {"message_id": "M0", "start": 0, "end": len(body),
                "text": body}
        return dict(span)

    def _event(self, task_type, evidence=None):
        return {"operation": "create", "source_msg": "M0",
                "evidence": list(evidence or ["M0"]),
                "details": {"action": "send", "object": "lease copy",
                            "type": task_type, "owner": "P1", "due": None}}

    def test_every_permitted_type_is_accepted(self):
        for task_type in _schema_enums()["task_type"]:
            self.assertIsNone(validate_event(self._event(task_type),
                                             self.observation, self.data))

    def test_invented_types_are_rejected(self):
        for task_type in ("task", "request", "alert"):
            with self.assertRaisesRegex(TaskError, "Invalid task type"):
                validate_event(self._event(task_type),
                               self.observation, self.data)

    def test_evidence_must_reference_valid_message_ids(self):
        with self.assertRaisesRegex(TaskError, "Unsupported event citations"):
            validate_event(self._event("commitment",
                                       evidence=["3a8057a55a648d8b"]),
                           self.observation, self.data)
        # The message-ID control still validates.
        self.assertIsNone(validate_event(self._event("followup"),
                                         self.observation, self.data))

    def test_unknown_owner_still_fail_closed(self):
        event = dict(self._event("commitment"))
        event["details"] = dict(event["details"], owner="P99")
        with self.assertRaisesRegex(TaskError, "Unknown owner"):
            validate_event(event, self.observation, self.data)


class ContractNeutralityTests(unittest.TestCase):
    """The contracts stay provider-neutral and versioned consistently."""

    def test_no_provider_or_model_tokens_in_governed_text(self):
        for text in (CONTEXT_PROMPT, _org_contract_text(),
                     _task_contract_text()):
            flat = " ".join(text.split()).casefold()
            for token in ("gemini", "gpt", "openai", "claude", "llama"):
                self.assertNotIn(token, flat)

    def test_version_bumps_are_consistent(self):
        source = _source("reasoning.py")
        self.assertEqual(CONTEXT_VERSION, "context-5")
        self.assertIn('prompt_version": "task-review-4"', source)
        self.assertNotIn('prompt_version": "task-review-3"', source)
        self.assertNotIn('CONTEXT_VERSION = "context-4"', source)


if __name__ == "__main__":
    unittest.main()
