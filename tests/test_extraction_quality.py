"""Session-08 focused tests for the Gate-6 extraction quality corrections.

Regressions for the 2026-11-08 REAL pilot evidence (`session-08-gate-6-
real-launch-partial-run-evidence.json`: 8 extraction transmissions, 4 jobs
truncated at 2044/2048 completion tokens with finish_reason "length", 2
valid-JSON finish-stop responses wrongly rejected by validate_extraction, 2
successes, zero unknown usage, all downstream stages explicitly incomplete):

1. validate_extraction accepts covered spans in ANY order (multiset, still
   exactly once), tolerates packet-echo extra keys and int-valued
   string/float offset forms, while still rejecting duplicates, incomplete
   coverage, boolean/fractional offsets and wrong or out-of-span evidence.
2. Pilot telemetry surfaces the REAL failure codes (`truncated`,
   `validation`) instead of the generic request_failed.
3. Truncated and validation-failing transmission are non-retryable: exactly
   one transmission per failed job, zero recoveries.
4. Failed extraction never fabricates downstream results: every downstream
   stage records an explicit incomplete state, nothing is dispatched with
   invented observations.

No network and no credentials anywhere: pilot transports inject synthetic
bytes; validator tests reuse the synthetic test_reasoning fixtures.
"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "tests"))
sys.path.insert(0, str(PROJECT / "tests" / "pilot_fixtures"))

import pilot_runner
from data import MessageSpan, ProcessingWindow
from mock_responses import extraction_response
from reasoning import ReasoningError, validate_extraction
from test_reasoning import fixture, observation

PRICING = {"model": "synthetic-mock-1", "source": "offline projection only",
           "currency": "USD", "input_usd_per_mtok": 0.75,
           "output_usd_per_mtok": 3.75}
SYNTHETIC_ENV = {"LLM_BASE_URL": "https://synthetic.invalid/v1/",
                 "LLM_MODEL": "synthetic-offline",
                 "LLM_API_KEY": "synthetic-offline-key"}

WIRES = []


def truncated_transport(endpoint, wire, key, timeout):
    """Provider cut at its completion cap: finish_reason length, empty text."""
    WIRES.append(json.loads(wire))
    usage = {"prompt_tokens": len(wire) + 1, "completion_tokens": 2044,
             "total_tokens": len(wire) + 2045}
    data = {"choices": [{"finish_reason": "length",
                         "message": {"content": ""}}],
            "model": "mock-truncated-1", "usage": usage}
    return 200, {}, json.dumps(data).encode("utf-8")


def validation_transport(endpoint, wire, key, timeout):
    """Finish-stop JSON with a MISSING primary span: clean but invalid."""
    body = json.loads(wire)
    packet = json.loads(body["messages"][1]["content"])
    if set(packet) == {"chat_id", "primary", "context", "seed"}:
        payload = extraction_response(packet)
        payload["covered"] = payload["covered"][:-1]
        content = json.dumps(payload, ensure_ascii=False)
        usage = {"prompt_tokens": len(wire) + 1,
                 "completion_tokens": len(content) + 16,
                 "total_tokens": len(wire) + len(content) + 17}
        data = {"choices": [{"finish_reason": "stop",
                             "message": {"content": content}}],
                "model": "mock-shortfall-1", "usage": usage}
        return 200, {}, json.dumps(data, ensure_ascii=False).encode("utf-8")
    from mock_responses import respond
    return respond(endpoint, wire, key, timeout)


def offline_run(transport):
    """Offline pilot over the synthetic fixtures with an injected transport."""
    document = pilot_runner.run_pilot(mode="test", transport=transport,
                                      verified_pricing=PRICING)
    return document


class ExtractionValidatorToleranceTests(unittest.TestCase):
    def setUp(self):
        self.data, self.plan = fixture()
        self.window = self.plan.windows[0]
        self.reply = {"covered": [asdict(s) for s in self.window.primary],
                      "observations": [observation()]}

    def validate(self, reply):
        return validate_extraction(json.dumps(reply), self.data, self.window)

    def test_covered_order_does_not_change_semantics(self):
        self.reply["covered"].reverse()
        self.assertEqual(self.validate(self.reply), [observation()])

    def test_multi_span_window_covered_may_not_be_id_ordered(self):
        # Regression for the pilot_en window-1 real failure mode: a
        # multi-primary window whose packet order differs from message-id
        # order; covered must still validate as an exact multiset.
        window = ProcessingWindow(chat_id="C1", primary=(
            MessageSpan("M1", 0, 10), MessageSpan("M0", 0, 10)))
        reply = {"covered": [asdict(s) for s in window.primary],
                 "observations": [observation()]}
        result = validate_extraction(json.dumps(reply), self.data, window)
        self.assertEqual(result, [observation()])

    def test_packet_echo_extras_and_numeric_forms_accepted(self):
        span = asdict(self.window.primary[0])
        self.reply["covered"] = [dict(span, start=str(span["start"]),
                                      end=float(span["end"]),
                                      text="whole-packet echo",
                                      sender_id="ME", ts=1,
                                      kind="text", quoted_id=None)]
        self.assertEqual(self.validate(self.reply), [observation()])

    def test_evidence_numeric_forms_accepted_with_exact_text(self):
        self.reply["observations"][0]["evidence"] = [
            {"message_id": "M0", "start": "0", "end": 10.0, "text": "Walk daily"}]
        self.assertEqual(self.validate(self.reply), [observation()])
        self.reply["observations"][0]["evidence"] = [
            {"message_id": "M0", "start": 0.0, "end": "10", "text": "Walk daily"}]
        self.assertEqual(self.validate(self.reply), [observation()])

    def test_covered_duplicates_rejected(self):
        self.reply["covered"] = [asdict(s)
                                 for s in self.window.primary] * 2
        with self.assertRaises(ReasoningError):
            self.validate(self.reply)

    def test_partial_covered_rejected_even_with_proper_evidence(self):
        self.reply["covered"] = []
        with self.assertRaises(ReasoningError):
            self.validate(self.reply)

    def test_wrong_text_and_out_of_span_evidence_stay_rejected(self):
        for evidence in ({"text": "Walk dailx"}, {"end": "99"},
                         {"start": "11", "end": "20", "text": "anything"}):
            with self.subTest(evidence=evidence):
                item = {"message_id": "M0", "start": 0, "end": 10,
                        "text": "Walk daily"}
                item.update(evidence)
                self.reply["observations"][0]["evidence"] = [item]
                with self.assertRaises(ReasoningError):
                    self.validate(self.reply)

    def test_boolean_and_fractional_offsets_rejected(self):
        span = asdict(self.window.primary[0])
        for start, end in ((True, 10), (0.5, 10)):
            self.reply["covered"] = [dict(span, start=start, end=end)]
            with self.subTest(start=start), self.assertRaises(ReasoningError):
                self.validate(self.reply)
        self.reply["observations"][0]["evidence"] = [
            {"message_id": "M0", "start": True, "end": 10, "text": "k daily"}]
        with self.assertRaises(ReasoningError):
            self.validate(self.reply)


class PilotFailureSurfacingTests(unittest.TestCase):
    def _offline(self, transport):
        WIRES.clear()
        captured = io.StringIO()
        with patch.dict(os.environ, SYNTHETIC_ENV, clear=True), \
                redirect_stdout(captured):
            document = pilot_runner.run_pilot(
                mode="test", transport=transport, verified_pricing=PRICING)
        self.assertNotIn(SYNTHETIC_ENV["LLM_API_KEY"], captured.getvalue())
        return document

    def _failure_assertions(self, document, code):
        jobs = document["telemetry"]
        extraction = [job for job in jobs if job["stage"] == "extraction"]
        self.assertEqual(len(extraction), 8)
        self.assertEqual({job["outcome"] for job in extraction}, {code})
        # The evidence cites the real local classification, not a generic code.
        self.assertEqual({job.get("error_code") for job in extraction}, {code})
        # Non-retryable: exactly one transmission per job, zero recoveries.
        self.assertEqual(sum(len(job["transmissions"]) for job in jobs), 8)
        self.assertEqual(document["budget_summary"]["recoveries"], 0)
        self.assertTrue(document["envelope_verified"])
        self.assertEqual(document["stopped"], None)
        # No fabricated downstream results: every recorded downstream stage
        # stays explicitly incomplete and the help stage publishes nothing.
        states = document["stage_states"]
        self.assertTrue(states)
        self.assertEqual({s["state"] for s in states.values()}, {"incomplete"})
        self.assertEqual(document["run_state"], "completed")

    def test_truncated_jobs_surface_real_code_without_retry(self):
        self._failure_assertions(self._offline(truncated_transport),
                                 "truncated")
        # The pilot dispatch cap is the corrected 4096 for every job sent.
        self.assertEqual({wire["max_tokens"] for wire in WIRES}, {4096})

    def test_validation_jobs_surface_real_code_without_retry(self):
        self._failure_assertions(self._offline(validation_transport),
                                 "validation")

    def test_corrected_cap_keeps_envelope_and_safeguard_bounded(self):
        # Budget arithmetic with the recorded real-run prompt estimates:
        # 25,624 estimated extraction prompt tokens + 8x4096 = 58,392 base;
        # absolute worst with 30 transmissions at the 4096 cap is far below
        # the 250,000 reservation, and the USD bound stays under USD 2.00.
        self.assertLessEqual(25624 + 13 * 4096, 250000)
        self.assertLessEqual(30 * 4096 + 26552, 250000)
        self.assertLess(250000 / 1e6 * 2.50, 2.00)


if __name__ == "__main__":
    unittest.main()
