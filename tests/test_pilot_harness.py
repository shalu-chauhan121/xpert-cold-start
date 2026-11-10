"""Session-04 offline tests for the pilot safety harness. No network, no keys."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

import llm
from pilot_harness import (PilotHarness, PilotLimits, PilotRefusal,
                           normalize_pricing, project_cost)

# Synthetic configuration ONLY (offline transport; never used for network).
ENV = {"LLM_BASE_URL": "https://synthetic.invalid/v1/",
       "LLM_API_KEY": "synthetic-secret", "LLM_MODEL": "synthetic-v1"}
PRICING_OK = {"model": "synthetic-v1", "source": "provider price list 2026-11",
              "currency": "USD", "input_usd_per_mtok": 0.5, "output_usd_per_mtok": 1.5}


def probe(index):
    """Unique message bodies: retries must not hit the response cache."""
    return [{"role": "user", "content": "Probe %d" % index}]


def body(usage):
    data = {"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
            "model": "synthetic-v1"}
    if usage is True:
        data["usage"] = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    elif isinstance(usage, dict):
        data["usage"] = usage
    return json.dumps(data).encode("utf-8")


class Recorder:
    """Injected transport: counts every dispatch; optional permanent failure."""

    def __init__(self, usage=True, status=200, fail_status=None):
        self.calls = []
        self.wires = []
        self.usage, self.status, self.fail_status = usage, status, fail_status

    def __call__(self, endpoint, wire, key, timeout):
        self.calls.append(endpoint)
        self.wires.append(wire)
        status = self.fail_status if self.fail_status is not None else self.status
        if not 200 <= status < 300:
            return status, {}, b""
        return status, {}, body(self.usage)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


NO_SLEEP = lambda seconds: None


class TestLimits(unittest.TestCase):
    def test_envelope_math(self):
        limits = PilotLimits()
        self.assertTrue(limits.validate())
        self.assertEqual(limits.base_calls, 25)
        self.assertEqual(limits.recovery_limit, 5)
        self.assertEqual(limits.max_transmissions, 30)


class TestPricing(unittest.TestCase):
    def test_verified_pricing_ok(self):
        verified = normalize_pricing(PRICING_OK)
        self.assertEqual(verified["currency"], "USD")
        self.assertEqual(verified["input_usd_per_mtok"], 0.5)
        self.assertEqual(verified["output_usd_per_mtok"], 1.5)

    def test_separate_rate_projection(self):
        # 250k input tokens at $0.5/Mtok input + 25k output tokens at $1.5/Mtok output.
        self.assertEqual(project_cost(0.5, 1.5, 250000, 25000), 0.1625)
        # The projection is the literal separate-rate sum.
        self.assertEqual(project_cost(0.5, 1.5, 250000, 25000) * 1e6,
                         0.5 * 250000 + 1.5 * 25000)
        self.assertLessEqual(project_cost(0.5, 1.5, 250000, 25000), PilotLimits().spend_ceiling_usd)
        self.assertGreater(project_cost(4.0, 100.0, 250000, 100000),
                           PilotLimits().spend_ceiling_usd)

    def test_pricing_fail_closed_variants(self):
        broken = [{}, {"model": "m", "source": "s"},
                  dict(PRICING_OK, input_usd_per_mtok=-0.5),
                  dict(PRICING_OK, output_usd_per_mtok="0.5"),
                  dict(PRICING_OK, input_usd_per_mtok=True),
                  dict(PRICING_OK, currency="EUR"),
                  dict(PRICING_OK, source="  "),
                  dict(PRICING_OK, output_usd_per_mtok=float("nan"))]
        for index, table in enumerate(broken):
            with self.subTest(index=index):
                # Real mode requires verified pricing before anything else.
                with patch.dict(os.environ, {k: "" for k in ENV}):
                    with self.assertRaises(PilotRefusal) as caught:
                        PilotHarness(verified_pricing=table)
                    self.assertEqual(caught.exception.code, "fail_closed")
                # Test mode refuses malformed pricing just as hard.
                recorder = Recorder()
                with self.assertRaises(PilotRefusal):
                    PilotHarness(transport=recorder, verified_pricing=table)
                self.assertEqual(len(recorder.calls), 0)  # nothing was dispatched

    def test_real_mode_missing_pricing_fails_closed(self):
        # Pricing absent entirely is the real-mode fail-closed case; test mode
        # legitimately runs with no pricing at all.
        with patch.dict(os.environ, {k: "" for k in ENV}):
            with self.assertRaises(PilotRefusal) as caught:
                PilotHarness(verified_pricing=None)
            self.assertEqual(caught.exception.code, "fail_closed")

    def test_real_mode_requires_controls_and_environment(self):
        with patch.dict(os.environ, ENV):
            with self.assertRaises(PilotRefusal) as caught:
                PilotHarness(verified_pricing=PRICING_OK)
            self.assertEqual(caught.exception.code, "fail_closed")  # controls unconfirmed
            with patch.dict(os.environ, {k: "" for k in ENV}):
                with self.assertRaises(PilotRefusal) as caught:
                    PilotHarness(verified_pricing=PRICING_OK,
                                 provider_controls_confirmed=True)
                self.assertEqual(caught.exception.code, "fail_closed")  # env unknown


class TestHarness(unittest.TestCase):
    def make(self, recorder, pricing=None):
        return PilotHarness(transport=recorder, sleep=NO_SLEEP, verified_pricing=pricing)

    def test_transmission_cap_thirty(self):
        recorder = Recorder()
        agent = self.make(recorder)
        with patch.dict(os.environ, ENV):
            for index in range(25):
                content = agent.request(messages=probe(index), job_id="job-%d" % index)
                self.assertEqual(content, "{}")
            # Retries of already-started jobs consume the 5 recovery records.
            plan = ["job-24", "job-23", "job-24", "job-23", "job-22"]
            for offset, job in enumerate(plan):
                agent.request(messages=probe(100 + offset), job_id=job)
            summary = agent.budget.summary()
            self.assertEqual(summary["attempts"], 30)
            self.assertEqual(summary["recoveries"], 5)
            self.assertEqual(len(recorder.calls), 30)
            # 31st transmission: refused by the harness before the client runs.
            with self.assertRaises(PilotRefusal) as caught:
                agent.request(messages=probe(999), job_id="job-25")
            self.assertEqual(caught.exception.code, "transmission_cap")
            self.assertEqual(len(recorder.calls), 30)
            self.assertEqual(agent.stopped, None)

    def test_recovery_cap_five(self):
        recorder = Recorder(fail_status=500)
        agent = self.make(recorder)
        codes = []
        with patch.dict(os.environ, ENV):
            for job in ("A", "B", "C", "D"):
                with self.assertRaises(llm.LLMError) as caught:
                    agent.request(messages=probe(hash(job)), job_id=job)
                codes.append(caught.exception.detail["code"])
            summary = agent.budget.summary()
            self.assertEqual(summary["recoveries"], 5)
            # The llm.Budget layer independently refuses further retries.
            with self.assertRaises(llm.LLMError) as caught:
                agent.client.request(messages=probe(5), job_id="C")
            self.assertEqual(caught.exception.detail["code"], "recovery_budget")
            self.assertEqual(len(recorder.calls), 9)
            # The harness refuses before dispatch as well (defense in depth).
            with self.assertRaises(PilotRefusal) as caught:
                agent.request(messages=probe(6), job_id="C")
            self.assertEqual(caught.exception.code, "recovery_cap")
            self.assertEqual(len(recorder.calls), 9)
            # 3+3+2+1 transport attempts, then none of any kind.

    def test_token_reservation_fail_closed(self):
        recorder = Recorder()
        agent = self.make(recorder)
        with patch.dict(os.environ, ENV):
            with self.assertRaises(llm.LLMError) as caught:
                agent.request(messages=[{"role": "user", "content": "x" * 300000}],
                              job_id="big")
            self.assertEqual(caught.exception.detail["code"], "token_budget")
        self.assertEqual(recorder.calls, [])  # nothing was reserved or dispatched

    def test_deadline_fail_closed(self):
        recorder = Recorder()
        clock = FakeClock()
        agent = PilotHarness(transport=recorder, clock=clock, sleep=NO_SLEEP)
        clock.now = 700.0  # after construction; beyond the 600 s network allowance
        with patch.dict(os.environ, ENV):
            with self.assertRaises(PilotRefusal) as caught:
                agent.request(messages=probe(1), job_id="late")
        self.assertEqual(caught.exception.code, "deadline_exhausted")
        self.assertEqual(recorder.calls, [])
        self.assertEqual(agent.stopped, "deadline_exhausted")
        with patch.dict(os.environ, ENV):
            with self.assertRaises(PilotRefusal) as caught:
                agent.request(messages=probe(2), job_id="late2")
            self.assertEqual(caught.exception.code, "stopped")

    def test_unknown_usage_stops_dispatch(self):
        recorder = Recorder(usage=False)
        agent = self.make(recorder)
        with patch.dict(os.environ, ENV):
            content = agent.request(messages=probe(1), job_id="u1")
            self.assertEqual(content, "{}")
            self.assertEqual(agent.stopped, "unknown_usage")
            summary = agent.budget.summary()
            self.assertEqual(summary["unknown_usage_attempts"], 1)
            with self.assertRaises(PilotRefusal) as caught:
                agent.request(messages=probe(2), job_id="u2")
            self.assertEqual(caught.exception.code, "stopped")
        self.assertEqual(len(recorder.calls), 1)

    def test_over_ceiling_stops_run(self):
        recorder = Recorder(usage={"prompt_tokens": 300000, "completion_tokens": 0,
                                   "total_tokens": 300000})
        agent = self.make(recorder)
        with patch.dict(os.environ, ENV):
            with self.assertRaises(llm.LLMError) as caught:
                agent.request(messages=probe(1), job_id="big")
            self.assertEqual(caught.exception.detail["code"], "token_budget")
            self.assertEqual(agent.stopped, "token_ceiling")
            with self.assertRaises(PilotRefusal) as caught:
                agent.request(messages=probe(2), job_id="after")
            self.assertEqual(caught.exception.code, "stopped")
        self.assertEqual(len(recorder.calls), 1)

    def test_spend_ceiling_with_verified_pricing(self):
        recorder = Recorder(usage={"prompt_tokens": 100, "completion_tokens": 900,
                                   "total_tokens": 1000})
        pricing = dict(PRICING_OK, input_usd_per_mtok=8.0, output_usd_per_mtok=1900.0)
        agent = self.make(recorder, pricing=pricing)
        with patch.dict(os.environ, ENV):
            content = agent.request(messages=probe(1), job_id="one", max_tokens=1900)
            self.assertEqual(content, "{}")
            projected = agent.projected_usd()
            self.assertGreater(projected, agent.limits.spend_ceiling_usd)
            with self.assertRaises(PilotRefusal) as caught:
                agent.request(messages=probe(2), job_id="two", max_tokens=1900)
            self.assertEqual(caught.exception.code, "spend_ceiling")
        self.assertEqual(len(recorder.calls), 1)

    def test_happy_path_with_usage(self):
        recorder = Recorder()
        agent = self.make(recorder)
        with patch.dict(os.environ, ENV):
            self.assertEqual(agent.request(messages=probe(1), job_id="a"), "{}")
            self.assertEqual(agent.request(messages=probe(2), job_id="b"), "{}")
        summary = agent.budget.summary()
        self.assertEqual(summary["attempts"], 2)
        self.assertEqual(summary["recoveries"], 0)
        self.assertEqual(summary["unknown_usage_attempts"], 0)
        self.assertFalse(summary["over_ceiling"])
        self.assertEqual(agent.stopped, None)
        self.assertEqual(agent.projected_usd(), None)  # no pricing: no projection
        self.assertEqual(len(recorder.calls), 2)


if __name__ == "__main__":
    unittest.main()
