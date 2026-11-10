"""Session-08 focused tests for the downstream quality correction.

Regressions for the REAL retry-run evidence
(`session-08-gate-6-pilot-retry-evidence.json`: 21 transmissions on 20 jobs;
8/8 extraction windows succeeded; the 9 dispatched downstream job failures
were 5x `validation` + 4x `malformed_content` across one Bengali HTTP-error
recovery, while pilot_en entities, both task matches and help were never
dispatched).

Diagnosed causes covered here:
- `malformed_content` = content failed strict JSON-object parsing although
  response_format json_object was requested. Smallest correction: shared
  tolerance in `validation.read_json` and `llm._validate` that unwraps ONE
  balanced {...} object from fences/prose before a strict re-parse with the
  same strict rules (duplicate keys, non-finite constants, non-object
  payloads still fail; no validator is loosened), plus raw-JSON-only prompt
  lines with bumped prompt versions. No invented response is assumed.
- `validation` failures are contract deviations inside parsed dicts, with
  NO retained bodies (disclosed). Correction = better SAFE local
  diagnostics: exception class name in the LLMError detail message and
  error_detail/http_status recorded on failed pilot jobs.
- The Bengali HTTP error: transient non-2xx on attempt 1, recovered exactly
  as designed (1 of 5 recoveries, unknown usage conserved).

Offline only: injected transports return synthetic bytes; no network and no
credentials.
"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "tests"))
sys.path.insert(0, str(PROJECT / "tests" / "pilot_fixtures"))

import llm
import pilot_runner
import reasoning
import validation
from reasoning import resolve_help
from tasks import TaskError, validate_event
from validation import ValidationError
from test_reasoning import fixture

ENV = {"LLM_BASE_URL": "https://synthetic.invalid/v1/",
       "LLM_MODEL": "synthetic-v1", "LLM_API_KEY": "synthetic-secret"}
PILOT_ENV = {"LLM_BASE_URL": "https://synthetic.invalid/v1/",
             "LLM_MODEL": "synthetic-offline",
             "LLM_API_KEY": "synthetic-offline-key"}
PRICING = {"model": "synthetic-mock-1", "source": "offline projection only",
           "currency": "USD", "input_usd_per_mtok": 0.75,
           "output_usd_per_mtok": 3.75}


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class JsonParseToleranceTests(unittest.TestCase):
    """read_json: strict parse first; ONLY one balanced object recovered."""

    def test_fenced_and_prose_wrapped_object_recovered(self):
        for text in ('```json\n{"a": [1, 2]}\n```\nshort remarks.\n',
                     'The requested decisions: {"groups": [], "rejected": '
                     '[], "pending": []} as agreed.'):
            text = text.replace("\n", " ") if "```" in text else text
            self.assertEqual(
                validation.read_json(io.StringIO(text)),
                json.loads(text[text.find("{"):text.rfind("}") + 1]))

    def test_strict_objects_and_arrays_unchanged(self):
        self.assertTrue(validation.read_json(io.StringIO('[1, 2]')), [1, 2])
        self.assertEqual(validation.read_json(io.StringIO('{"a": "x"}')),
                         {"a": "x"})

    def test_duplicate_keys_still_rejected(self):
        for text in ('{"a": 1, "a": 2}',
                     '```json\n{"a": 1, "a": 2}\n```'):
            with self.assertRaises(ValueError):
                validation.read_json(io.StringIO(text))

    def test_nonfinite_still_rejected_and_braces_in_strings_skipped(self):
        with self.assertRaises(ValueError):
            validation.read_json(io.StringIO('{"a": NaN}'))
        self.assertEqual(validation.read_json(
            io.StringIO('note: {"a": "b} { c"} trailing')),
            {"a": "b} { c"})

    def test_prose_without_object_raises(self):
        with self.assertRaises(ValueError):
            validation.read_json(io.StringIO('no object here at all'))


class ClientValidationTests(unittest.TestCase):
    """llm._validate regressions for the malformed_content classification."""

    CHAT = [{"role": "user", "content": "synthetic"}]

    def _chat(self, content, validate=None):
        def transport(endpoint, body, key, timeout):
            data = {"choices": [{"finish_reason": "stop",
                                 "message": {"content": content}}],
                    "model": "synthetic-v1",
                    "usage": {"prompt_tokens": 12, "completion_tokens": 8,
                              "total_tokens": 20}}
            return 200, {}, json.dumps(data).encode("utf-8")
        with patch.dict(os.environ, ENV, clear=True):
            client = llm.Client(transport=transport, clock=Clock(),
                                sleep=Clock().sleep)
            return client.request(self.CHAT, None, None, 30,
                                  {"type": "json_object"}, 6,
                                  validate=validate)

    def test_fenced_json_objects_pass(self):
        for content in ('```json\n{"a": [1, 2]}\n```',
                        'Decisions: {"a": 1} as required.',
                        '{"a": 1}'):
            self.assertEqual(self._chat(content), content)

    def test_non_object_and_nonsense_stay_malformed(self):
        for content in ('[1, 2]', 'plain prose only'):
            with self.assertRaises(llm.LLMError) as caught:
                self._chat(content)
            self.assertEqual(caught.exception.detail["code"],
                             "malformed_content")

    def test_validation_detail_carries_local_class_name_only(self):
        def validate(_value):
            raise reasoning.ReasoningError("Invalid organisation group")
        with self.assertRaises(llm.LLMError) as caught:
            self._chat('{"a": 1}', validate=validate)
        self.assertEqual(caught.exception.detail["code"], "validation")
        self.assertIn("(ReasoningError)", caught.exception.detail["message"])
        self.assertNotIn(ENV["LLM_API_KEY"], caught.exception.detail["message"])


class HelpDependencyTests(unittest.TestCase):
    def test_invalid_five_array_candidate_fails_closed_without_dispatch(self):
        data, plan = fixture()
        empty = {"state": "incomplete", "required": [], "completed": [],
                 "failures": [], "pending": [], "unresolved": [], "tasks": [],
                 "searches": []}
        output = {name: [] for name in ("people", "organisations", "chats",
                                        "goals", "open_loops")}

        class Refusing:
            def request(self, *args, **kwargs):
                raise AssertionError("Prerequisite-incomplete help must not "
                                     "dispatch anything.")

        # Without resolved chat targets a five-array candidate cannot be
        # valid; resolve_help surfaces ValidationError (the pilot records
        # it as an explicit failure) and publishes nothing.
        with self.assertRaises(ValidationError):
            resolve_help(data, output, empty, Refusing())


def _mock_transport():
    from mock_responses import respond
    return respond


def _packet(wire):
    return json.loads(json.loads(wire)["messages"][1]["content"])


class PilotFailureTests(unittest.TestCase):
    def _offline(self, transport):
        captured = io.StringIO()
        with patch.dict(os.environ, PILOT_ENV, clear=True), \
                redirect_stdout(captured):
            document = pilot_runner.run_pilot(
                mode="test", transport=transport, clock=Clock(),
                sleep=Clock().sleep, verified_pricing=PRICING)
        self.assertNotIn(PILOT_ENV["LLM_API_KEY"], captured.getvalue())
        return document

    def _job(self, document, pack, label):
        return [job for job in document["telemetry"]
                if job["pack"] == pack and job["label"] == label]

    def test_offline_accounting_all_25_planned_dispatch(self):
        document = self._offline(_mock_transport())
        self.assertEqual(document["run_state"], "completed")
        self.assertEqual(document["budget_summary"]["attempts"], 25)
        self.assertEqual(document["planned"], 25)
        self.assertEqual(pilot_runner.count_plan()["planned_base_calls"], 25)
        self.assertEqual(pilot_runner.count_plan()["extraction"], 8)
        self.assertEqual(pilot_runner.count_plan()["organisations"], 2)
        self.assertEqual(pilot_runner.count_plan()["entities"], 3)
        self.assertEqual(pilot_runner.count_plan()["goals"], 2)
        self.assertEqual(pilot_runner.count_plan()["task_interpretation"], 7)
        self.assertEqual(pilot_runner.count_plan()["task_matching"], 2)
        self.assertEqual(pilot_runner.count_plan()["help"], 1)
        self.assertTrue(document["envelope_verified"])

    def test_transient_http_error_recovers_exactly_once(self):
        base, seen = _mock_transport(), {"interpret": False}

        def transport(endpoint, wire, key, timeout):
            try:
                packet = _packet(wire)
            except (ValueError, KeyError, TypeError, UnicodeError):
                return base(endpoint, wire, key, timeout)
            if packet.get("phase") == "interpret" and not seen["interpret"]:
                seen["interpret"] = True
                return 500, {}, b""
            return base(endpoint, wire, key, timeout)

        document = self._offline(transport)
        summary = document["budget_summary"]
        self.assertEqual(summary["attempts"], 26)
        self.assertEqual(summary["retries"], 1)
        self.assertEqual(summary["recoveries"], 1)
        # The unknown-usage attempt is conserved; the offline mock's entity
        # 'transport' artifacts also count unknown attempts, so >= 1.
        self.assertGreaterEqual(summary["unknown_usage_attempts"], 1)
        saved = next(job for job in document["telemetry"]
                     if len(job["transmissions"]) > 1)
        self.assertEqual(saved["transmissions"][0]["outcome"], "http_error")
        # The HTTP status is now persisted per transmission, closing the
        # real Bengali-run limitation where the status was unrecoverable.
        self.assertEqual(saved["transmissions"][0]["http_status"], 500)
        self.assertIsNone(saved["transmissions"][1]["http_status"])
        self.assertEqual(saved["transmissions"][1]["outcome"], "success")
        self.assertEqual(saved["outcome"], "success")

    def test_malformed_content_never_retries_and_fabricates_nothing(self):
        base = _mock_transport()

        def transport(endpoint, wire, key, timeout):
            try:
                packet = _packet(wire)
            except (ValueError, KeyError, TypeError, UnicodeError):
                return base(endpoint, wire, key, timeout)
            if packet.get("phase") == "interpret":
                data = {"choices": [{"finish_reason": "stop",
                                     "message": {
                                         "content": "Sorry, one plain "
                                                    "sentence instead."}}],
                        "model": "mock-prose-1",
                        "usage": {"prompt_tokens": 10, "completion_tokens": 9,
                                  "total_tokens": 19}}
                return 200, {}, json.dumps(data).encode("utf-8")
            return base(endpoint, wire, key, timeout)

        document = self._offline(transport)
        interpretations = [job for job in document["telemetry"]
                           if job["label"] == "task_interpret"]
        self.assertEqual(len(interpretations), 7)
        self.assertEqual({job["outcome"] for job in interpretations},
                         {"malformed_content"})
        self.assertEqual(sum(len(job["transmissions"]) for job in
                             interpretations), 7)
        self.assertEqual(document["budget_summary"]["recoveries"], 0)
        self.assertEqual(document["budget_summary"]["retries"], 0)
        for job in interpretations:
            self.assertIn("does not satisfy", job["error_detail"])
        # No matching phase dispatched without interpretations; every task
        # stage stays explicitly incomplete; nothing fabricated anywhere.
        self.assertNotIn("task_match", {job["label"] for job
                                        in document["telemetry"]})
        task_states = {key: value for key, value
                       in document["stage_states"].items()
                       if key.endswith("/tasks")}
        self.assertEqual(len(task_states), 4)
        self.assertTrue(all(value["state"] == "incomplete"
                            for value in task_states.values()))
        # Real-run replica: with every interpretation malformed, no open
        # ledger tasks exist, so the help stage records its explicit
        # prerequisite-gated failure WITHOUT dispatching any help job.
        help_state = document["stage_states"]["pilot_en/help"]
        self.assertEqual(help_state["state"], "incomplete")
        self.assertEqual(help_state["failures"], 1)
        self.assertFalse([job for job in document["telemetry"]
                          if job["label"] == "help"])

    def test_failed_organisation_gates_entities_without_dispatch(self):
        base, seen = _mock_transport(), {"org": 0}

        def transport(endpoint, wire, key, timeout):
            try:
                packet = _packet(wire)
            except (ValueError, KeyError, TypeError, UnicodeError):
                return base(endpoint, wire, key, timeout)
            if (set(packet) == {"contract", "observations", "seed", "as_of"}
                    and not seen["org"]):
                seen["org"] = True
                data = {"choices": [{"finish_reason": "stop",
                                     "message": {"content":
                                                 json.dumps({"groups": [],
                                                             "pending": []})}}],
                        "model": "mock-org-1",
                        "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                                  "total_tokens": 15}}
                return 200, {}, json.dumps(data).encode("utf-8")
            return base(endpoint, wire, key, timeout)

        document = self._offline(transport)
        org = self._job(document, "pilot_en", "organisations")
        self.assertEqual(len(org), 1)
        self.assertEqual(org[0]["outcome"], "validation")
        self.assertEqual(org[0]["error_code"], "validation")
        self.assertIn("(ReasoningError)", org[0]["error_detail"])
        # The English entity stage was planned but NEVER dispatched and its
        # state stays explicitly incomplete - no observations invented.
        self.assertFalse(self._job(document, "pilot_en", "entities"))
        entity_state = document["stage_states"]["pilot_en/entities"]
        self.assertEqual(entity_state["state"], "incomplete")
        self.assertEqual(entity_state["failures"], 0)
        # Later packs continued normally (pilot_bn organisations dispatched).
        self.assertTrue(self._job(document, "pilot_bn", "organisations"))
        # The help stage cannot complete: its organisation prerequisite
        # stays unresolved (remaining prerequisite work), regardless of the
        # mock allowlist's offline validation artifact.
        self.assertEqual(document["stage_states"]["pilot_en/help"]["state"],
                         "incomplete")


class PromptVersionsTests(unittest.TestCase):
    def test_contract_guidance_and_prompt_versions_bumped(self):
        self.assertIn("Respond with only one raw JSON object under "
                      "response_format",
                      reasoning.CONTEXT_PROMPT)
        self.assertIn("json_object: no markdown fences, prose or trailing "
                      "text.", reasoning.CONTEXT_PROMPT)
        # Session-08 retry-2 captured-failure regressions (context-4):
        # envelope exclusivity (never echo the schema alongside decisions)
        # and strict double-quoted JSON keys (no Python-style unquoted keys).
        self.assertIn("never echo the supplied schema", reasoning.CONTEXT_PROMPT)
        self.assertIn("All JSON keys and strings", reasoning.CONTEXT_PROMPT)
        self.assertIn("must be double-quoted", reasoning.CONTEXT_PROMPT)
        self.assertIn("no unquoted keys", reasoning.CONTEXT_PROMPT)
        self.assertEqual(reasoning.CONTEXT_VERSION, "context-5")
        # Extraction contract now forbids name-in-subjects (the "HomeServe"
        # captured failure) with a bumped version; wrap-tolerant matching.
        flat_prompt = " ".join(reasoning.EXTRACTION_PROMPT.split())
        self.assertIn("never place names, organisation names or invented "
                      "identifiers there", flat_prompt)
        self.assertEqual(reasoning.EXTRACTION_VERSION, "extract-2")
        source = (Path(__file__).resolve().parents[1] / "reasoning.py"
                  ).read_text(encoding="utf-8")
        self.assertIn('prompt_version": "task-review-4"', source)
        self.assertIn("never an observation ID, hash or", source)
        # The review prompt's raw-JSON line is wrapped in the source.
        self.assertIn("Respond with only one raw ", source)
        self.assertIn("JSON object: no markdown fences, prose or "
                      "trailing text.", source)


class TaskInterpretContractTests(unittest.TestCase):
    """Valid and invalid interpretation events over the production validator."""

    def _observation(self):
        data, plan = fixture()
        return data, dict({"kind": "task_create", "subjects": ["ME"],
                           "meaning": "A proposed walking habit",
                           "evidence": [{"message_id": "M0", "start": 0,
                                         "end": 10, "text": "Walk daily"}]},
                          id="a", windows=["w"])

    def test_valid_create_event_passes(self):
        data, observation = self._observation()
        event = {"operation": "create", "source_msg": "M0",
                 "evidence": ["M0"],
                 "details": {"action": "walk", "object": "daily",
                             "type": "commitment", "owner": "ME",
                             "due": None}}
        validate_event(event, observation, data)

    def test_invalid_operations_and_details_rejected(self):
        data, observation = self._observation()
        bad = ({"operation": "close", "source_msg": "M0",
                "evidence": ["M0"], "details": {}},
               {"operation": "create", "source_msg": "M2",  # not supplied
                "evidence": ["M2"], "details": {}},
               {"operation": "update", "source_msg": "M0",
                "evidence": ["M0"],
                "details": {"status": "done"}},           # unsupported field
               {"operation": "create", "source_msg": "M0",
                "evidence": ["M0"],
                "details": {"action": "write", "object": "mail",
                            "type": "promise", "owner": "ME", "due": None}},
               {"operation": "complete", "source_msg": "M0",
                "evidence": ["M0"], "details": {"owner": "P1"}})
        for event in bad:
            with self.subTest(operation=event["operation"]), \
                    self.assertRaises(TaskError):
                validate_event(event, observation, data)


if __name__ == "__main__":
    unittest.main()
