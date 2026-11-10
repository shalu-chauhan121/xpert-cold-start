"""Offline regressions for the Session-08 retry-2 captured response failures.

Source evidence (never modified, synthetic packs only):
`ai-logs/opencode/session-08-gate-6-pilot-retry-2-captures.json`
(created 2026-11-09T07:42:26Z, 18 captures, `synthetic_only: true`).

Each test reproduces one REAL captured failure shape offline and asserts the
production fail-closed behavior is unchanged. These are contract regressions,
not model-quality claims: no live model, no challenge data, no credentials.

Captured failure classes and their root causes:
1. `validation` on `extract:cb9459…:1` (pilot_en): the observation used the
   organisation NAME "HomeServe" as a `subjects` entry instead of an
   existing person/chat ID -> `ReasoningError("Unknown observation subject")`.
   Fix direction: `EXTRACTION_PROMPT` (extract-2) now explicitly forbids
   name subjects. The validator stays fail-closed.
2. `malformed_content` on `goals:fcce90…` (pilot_hi): valid-structure JSON
   with ONE unquoted key (`title:` Python style) under response_format
   json_object. Strict-first parsing plus outermost-object recovery cannot
   repair unquoted keys and MUST NOT; the run fails closed instead. Fix
   direction: `CONTEXT_PROMPT` (context-4) now requires double-quoted keys.
3. `validation` on `entities:bc2979…`/`entities:0af5ff…` (hi/bn): the exact
   `{decisions}` envelope was returned but the model ALSO echoed four extra
   top-level keys (`people`, `goals`, `open_loops`, `organisations`), and in
   the bn case a positive record (P04, circle vendor) carried empty evidence.
   Fix direction: `CONTEXT_PROMPT` (context-4) forbids top-level keys beyond
   the contract, and the entity contract (entity-3 text) requires nonempty
   evidence for every nonempty record unless the seed fixes the fields.
4. `validation` on `task-review:072d03…` (pilot_bn): the event cited the
   observation's hash identifier inside `evidence` instead of a message ID.
   Fix direction: the task-review prompt (task-review-3) requires message-ID
   evidence. `tasks.validate_event` stays fail-closed.
5. Transient HTTP 503s (extract:cb9459…:0, entities:0af5ff… attempt 1) were
   already handled exactly as designed (bounded retry/recovery); covered by
   the pre-existing `test_stage_quality` transient tests, not repeated here.
"""
import json
import unittest
from dataclasses import asdict
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "tests"))

from data import InputRecord
from reasoning import (validate_extraction, resolve_entities, ReasoningError,
                       CONTEXT_PROMPT, EXTRACTION_PROMPT)
from tasks import validate_event, TaskError
from validation import read_json
from test_reasoning import fixture
from test_reasoning_resolution import extracted, obs


def _span(record, message_id="M0"):
    body = record.original["body"]
    return {"message_id": message_id, "start": 0, "end": len(body), "text": body}


class ExtractionSubjectNameTests(unittest.TestCase):
    """Captured class 1: an organisation NAME inside `subjects`."""

    def setUp(self):
        self.data, self.plan = fixture()

    def _reply(self, subjects):
        window = self.plan.windows[0]
        return {"covered": [asdict(span) for span in window.primary],
                "observations": [{"kind": "organisation", "subjects": subjects,
                                  "meaning": "Appliance service updates are "
                                             "routed through the portal",
                                  "evidence": [_span(self.data.messages_by_id["M0"])]}]}

    def test_captured_name_subject_is_rejected_fail_closed(self):
        with self.assertRaisesRegex(ReasoningError, "Unknown observation subject"):
            validate_extraction(json.dumps(self._reply(["HomeServe"])),
                                self.data, self.plan.windows[0])

    def test_real_id_subject_still_accepted(self):
        # Sanity/anti-overfit control: the corrected contract direction
        # (names belong in meaning, IDs in subjects) still validates.
        result = validate_extraction(json.dumps(self._reply([])),
                                     self.data, self.plan.windows[0])
        self.assertEqual(result, self._reply([])["observations"])

    def test_unlocked_subject_prompts_are_model_agnostic(self):
        doubled = " ".join(EXTRACTION_PROMPT.split())
        for provider_token in ("gemini", "gpt", "openai", "claude"):
            self.assertNotIn(provider_token, doubled)


class UnquotedKeyContentTests(unittest.TestCase):
    """Captured class 2: one unquoted JSON key inside a json_object reply."""

    CAPTURED_GOALS = ('{\n  "groups": [\n    {"members": ["878f31c54f93d97a"],'
                      '\n     "record": {\n        "area": "health",'
                      '\n        "horizon": "3mo",'
                      '\n        title: "Run a half marathon in January",'
                      '\n        "type": "experience"\n      },'
                      '\n     "support": []\n    }\n  ],'
                      '\n  "pending": [],\n  "rejected": []\n}')

    def test_unquoted_key_is_not_repaired_and_fails_malformed(self):
        import io
        from llm import LLMError, Client
        # The shared reader (strict first, then ONE balanced object) still
        # rejects Python-style unquoted keys - no silent mis-parse.
        with self.assertRaises(ValueError):
            read_json(io.StringIO(self.CAPTURED_GOALS))
        # The client classifies it exactly as the real run recorded.
        with self.assertRaises(LLMError) as caught:
            Client._validate(self.CAPTURED_GOALS, {"type": "json_object"}, None)
        self.assertEqual(caught.exception.detail["code"], "malformed_content")


class EntityEnvelopeEchoTests(unittest.TestCase):
    """Captured class 3: decisions envelope PLUS echoed top-level keys."""

    def _observations(self):
        record = self.data.messages_by_id["M0"]
        candidate = dict(obs("person", "p"), evidence=[_span(record)])
        return extracted([candidate])

    def setUp(self):
        self.data, self.plan = fixture()
        self.data.seed = {"circles": {"P1": "child"}}
        # Broadcast decisions for BOTH required targets, as the real run did.
        self.decisions = [
            {"category": "people", "id": "P1",
             "record": {"id": "P1", "circle": "child"}, "evidence": ["p"]},
            {"category": "chats", "id": "C1",
             "record": {"chat_id": "C1", "person": "P1"}, "evidence": ["p"]},
        ]

    def _entities(self, reply):
        from test_reasoning import FakeClient
        return resolve_entities(self.data, self._observations(),
                                {"state": "succeeded_empty", "items": []},
                                FakeClient([reply]))

    def test_captured_envelope_echo_is_rejected_fail_closed(self):
        echo = {"decisions": list(self.decisions), "people": [],
                "organisations": [], "chats": [], "goals": [], "open_loops": []}
        result = self._entities(echo)
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(len(result["people"]), 0)
        self.assertEqual(len(result["chats"]), 0)
        self.assertEqual([f["code"] for f in result["failures"]],
                         ["entity_resolution_failed"])

    def test_envelope_only_equivalent_reply_succeeds(self):
        # Anti-overfit control: the same decisions under the correct envelope,
        # mirroring the real hi/bn intent, remain a legitimate success - the
        # fix tightened the CONTRACT, it did not invent a passable response.
        result = self._entities({"decisions": list(self.decisions)})
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual([p["id"] for p in result["people"]], ["P1"])
        self.assertEqual([c["chat_id"] for c in result["chats"]], ["C1"])

    def test_entity_contract_requires_nonempty_evidence_on_positive_records(self):
        # The bn capture's second deviation: positive record, empty evidence.
        empty_evidence = [dict(self.decisions[0], evidence=[])]
        result = self._entities({"decisions": empty_evidence})
        self.assertEqual(result["state"], "incomplete")


class TaskEvidenceIdentifierTests(unittest.TestCase):
    """Captured class 4: observation hash cited as event evidence."""

    def setUp(self):
        self.data, self.plan = fixture()
        self.observation = dict({"kind": "task_update", "subjects": ["P1"],
                                 "meaning": "Lease copy will be sent tomorrow",
                                 "id": "3a8057a55a648d8b7b2ab10af2d61e0f"},
                                evidence=[_span(self.data.messages_by_id["M0"])])

    def test_captured_observation_hash_citation_rejected(self):
        event = {"operation": "ambiguous", "source_msg": "M0",
                 "evidence": ["3a8057a55a648d8b7b2ab10af2d61e0f"], "details": {}}
        with self.assertRaisesRegex(TaskError, "Unsupported event citations"):
            validate_event(event, self.observation, self.data)

    def test_message_id_citation_still_accepted(self):
        event = {"operation": "ambiguous", "source_msg": "M0",
                 "evidence": ["M0"], "details": {}}
        self.assertIsNone(validate_event(event, self.observation, self.data))


class ContextPromptModelAgnosticismTests(unittest.TestCase):
    def test_no_provider_or_model_names_in_production_prompts(self):
        for prompt in (CONTEXT_PROMPT, EXTRACTION_PROMPT):
            flat = " ".join(prompt.split()).casefold()
            for token in ("gemini", "gpt-", "openai", "claude", "llama"):
                self.assertNotIn(token, flat)


if __name__ == "__main__":
    unittest.main()
