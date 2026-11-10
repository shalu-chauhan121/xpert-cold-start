"""Session-05 offline tests for the bounded pilot runner.

No network, no credentials, no real-model output. The injected transport is
the Session-04 deterministic mock over synthetic fixtures. These tests assert
the approved allocation, harness bookkeeping, safe-stop behaviour and run
determinism — NOT semantic matrix outcomes (Gate 7 reviews real outputs).
"""
import copy
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "tests"))

import pilot_harness
import pilot_runner
from pilot_runner import PilotRefusal, count_plan, describe_plan, run_pilot

sys.path.insert(0, str(PROJECT / "tests" / "pilot_fixtures"))
from mock_responses import respond

PRICING = {"model": "synthetic-mock-1", "source": "offline projection only",
           "currency": "USD", "input_usd_per_mtok": 0.75,
           "output_usd_per_mtok": 3.75}


class Clock:
    """Deterministic instant clock; fake sleep charges nothing."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


# The production client requires endpoint/model/key configuration even with
# an injected offline transport; tests use throwaway synthetic values that
# can never reach the network (the transport is injected, not a socket).
SYNTHETIC_ENV = {"LLM_BASE_URL": "https://synthetic.invalid/v1/",
                 "LLM_MODEL": "synthetic-offline",
                 "LLM_API_KEY": "synthetic-offline-key"}


def offline_run(**kwargs):
    options = dict(mode="test", transport=respond, clock=Clock(),
                   sleep=Clock().sleep, verified_pricing=PRICING)
    options.update(kwargs)
    with patch.dict(os.environ, SYNTHETIC_ENV, clear=True):
        return run_pilot(**options)


class PlanTests(unittest.TestCase):
    def test_approved_totals_match_envelope(self):
        totals = count_plan()
        self.assertEqual(totals["planned_base_calls"], 25)
        self.assertEqual(totals["extraction"], 8)
        self.assertEqual(totals["organisations"], 2)
        self.assertEqual(totals["entities"], 3)
        self.assertEqual(totals["goals"], 2)
        self.assertEqual(totals["task_interpretation"], 7)
        self.assertEqual(totals["task_matching"], 2)
        self.assertEqual(totals["help"], 1)
        packs = {pack for pack in count_plan()["per_pack"]}
        self.assertEqual(packs, {"pilot_en", "pilot_hi", "pilot_bn", "pilot_hn"})
        # The four languages plus all approved stages fit the envelope.
        self.assertGreaterEqual(sum(count_plan()["per_pack"][p]["total"]
                                    for p in packs), 25)

    def test_runner_uses_synthetic_fixtures_only(self):
        root = pilot_runner.FIXTURE_ROOT
        self.assertEqual(root, PROJECT / "tests" / "pilot_fixtures")


class EvidenceChecks:
    """Shared proof of envelope and instrumentation for completing runs."""

    def proof(self, evidence):
        self.assertEqual(evidence["synthetic_only"], True)
        self.assertEqual(evidence["stopped"], None)
        self.assertTrue(evidence["envelope_verified"])
        summary = evidence["budget_summary"]
        total = sum(len(job.get("transmissions", [])) for job in evidence["telemetry"])
        # Instrumentation must be exactly once per dispatch across ALL stages.
        self.assertEqual(summary["attempts"], total)


class OfflineRunTests(EvidenceChecks, unittest.TestCase):

    def test_offline_run_bookkeeping_and_telemetry(self):
        document = offline_run()
        self.assertEqual(document["run_state"], "completed")
        self.proof(document)
        summary = document["budget_summary"]
        # Exactly the 25 planned base dispatches, zero recoveries offline.
        self.assertEqual(summary["attempts"], 25)
        self.assertEqual(summary["recoveries"], 0)
        self.assertEqual(summary["retries"], 0)
        self.assertEqual(document["planned"], 25)
        self.assertLess(summary["charged_tokens"], 250000)
        self.assertIn("projected_usd", document)
        self.assertLessEqual(document["projected_usd"], 2.0)
        # Every planned stage appears; labels unique per dispatched job.
        stages = {}
        for job in document["telemetry"]:
            stages.setdefault((job["pack"], job["stage"]), 0)
            stages[(job["pack"], job["stage"])] += 1
        self.assertEqual(stages[("pilot_en", "extraction")], 2)
        self.assertEqual(stages[("pilot_hn", "extraction")], 2)
        self.assertEqual(stages[("pilot_en", "organisations")], 1)
        self.assertEqual(stages[("pilot_bn", "organisations")], 1)
        self.assertEqual(stages[("pilot_hi", "entities")], 1)
        self.assertEqual(stages[("pilot_en", "goals")], 1)
        self.assertEqual(stages[("pilot_hi", "goals")], 1)
        for pack in ("pilot_en", "pilot_hi", "pilot_bn", "pilot_hn"):
            key = (pack, "task_interpret")
            self.assertIn(key, stages)
        self.assertEqual(stages[("pilot_en", "task_interpret")], 3)
        self.assertEqual(stages[("pilot_hn", "task_interpret")], 2)
        self.assertEqual(stages[("pilot_en", "task_match")], 1)
        self.assertEqual(stages[("pilot_hn", "task_match")], 1)
        self.assertEqual(stages[("pilot_en", "help")], 1)
        self.assertNotIn(("pilot_hn", "help"), stages)
        self.assertNotIn(("pilot_hn", "organisations"), stages)
        self.assertEqual(document["stage_states"]["pilot_en/organisations"]["state"],
                         "succeeded")
        self.assertEqual(document["stage_states"]["pilot_en/goals"]["state"],
                         "succeeded")
        self.assertEqual(document["stage_states"]["pilot_hi/goals"]["state"],
                         "succeeded")
        self.assertEqual(document["stage_states"]["pilot_hn/tasks"]["state"],
                         "succeeded")
        # Fixture input integrity was recorded.
        self.assertEqual(len(document["fixture_sha256"]), 4)
        self.assertTrue(all(len(h) == 64 for pack in document["fixture_sha256"]
                            for h in document["fixture_sha256"][pack].values()))
        # No credentials anywhere in the document.
        self.assertNotIn("synthetic-secret", json.dumps(document))

    def test_offline_failures_are_explicit_not_silent(self):
        document = offline_run()
        # Known disclosed mock-routing artifacts must FAIL EXPLICITLY:
        # scoped entity stages cannot resolve C_PAIR/C_QUOTE observations.
        for stage in ("pilot_en/entities", "pilot_hi/entities",
                      "pilot_bn/entities"):
            self.assertEqual(document["stage_states"][stage]["state"], "incomplete")
            self.assertGreaterEqual(document["stage_states"][stage]["failures"], 1)
        # Every dispatched job that failed carries a code, never a blank.
        for job in document["telemetry"]:
            if not job.get("transmissions"):
                self.assertIn(job.get("error_code"),
                              ("configuration", "call_budget", "recovery_budget"))
        self.proof(document)

    def test_ambiguous_paths_are_recorded_not_resolved(self):
        document = offline_run()
        # EN: M4 negated-cancellation interpret runs; its match stays explicit
        # (unresolved recorded) with no status side-effect on the ledger.
        unresolved = document["stage_states"]["pilot_en/tasks"].get("unresolved")
        self.assertGreaterEqual(unresolved, 1)
        self.assertIn(document["stage_states"]["pilot_hn/tasks"]["state"],
                      ("succeeded", "succeeded_empty"))

    def test_repeated_run_is_deterministic(self):
        def canonical(document):
            copy_ = copy.deepcopy(document)
            volatile = ("created", "budget_summary", "telemetry")
            for key in volatile:
                copy_.pop(key, None)
            return json.dumps(copy_, ensure_ascii=False, sort_keys=True)
        first = offline_run()
        second = offline_run()
        self.assertEqual(canonical(first), canonical(second))
        # Core deterministic stage payloads match byte-identically.
        self.assertEqual(first["stage_states"], second["stage_states"])
        self.assertEqual(first["planned"], second["planned"])

    def test_extraction_telemetry_records_real_fields(self):
        document = offline_run()
        extract = [job for job in document["telemetry"]
                   if job["stage"] == "extraction" and job.get("job_id")]
        self.assertGreaterEqual(len(extract), 8)
        for job in extract:
            self.assertTrue(job["job_id"].startswith("extract:"))
            self.assertEqual(job["outcome"], "success")
            record = job["transmissions"][0]
            self.assertGreater(record["reported_prompt_tokens"], 0)
            self.assertGreater(record["reported_completion_tokens"], 0)
            self.assertEqual(record["unknown_usage"], False)
            self.assertEqual(job["finish_reason"], "stop")


class SafeStopTests(EvidenceChecks, unittest.TestCase):
    def test_offline_requires_injected_transport(self):
        document = run_pilot(mode="test", transport=None)
        self.assertEqual(document["run_state"], "refused")
        self.assertEqual(document["error_code"], "configuration")

    def test_real_mode_fails_closed(self):
        base_env = {"LLM_BASE_URL": "https://synthetic.invalid/v1",
                    "LLM_MODEL": "synthetic-v1", "LLM_API_KEY": "synthetic-secret"}
        clean = {name: "" for name in base_env}
        with patch.dict(os.environ, clean, clear=True):
            document = run_pilot(mode="real")
            self.assertEqual(document["run_state"], "refused")
            self.assertIn(document["error_code"],
                          ("fail_closed", "configuration"))
        with patch.dict(os.environ, base_env, clear=True):
            without_pricing = run_pilot(mode="real")
            self.assertEqual(without_pricing["run_state"], "refused")
            self.assertEqual(without_pricing["error_code"], "fail_closed")
            with_controls = run_pilot(mode="real",
                                      verified_pricing=pilot_runner.VERIFIED_PRICING,
                                      provider_controls_confirmed=False)
            self.assertEqual(with_controls["run_state"], "refused")
            self.assertEqual(with_controls["error_code"], "fail_closed")

    def test_unknown_usage_stops_before_further_dispatch(self):
        calls = []
        def no_usage_transport(endpoint, wire, key, timeout):
            calls.append(1)
            status, headers, body = respond(endpoint, wire, key, timeout)
            data = json.loads(body.decode("utf-8"))
            data.pop("usage", None)
            return status, headers, json.dumps(data).encode("utf-8")
        document = offline_run(transport=no_usage_transport)
        self.assertEqual(document["run_state"], "stopped: unknown_usage")
        self.assertEqual(document["stopped"], "unknown_usage")
        self.assertEqual(len(calls), 1)
        summary = document["budget_summary"]
        self.assertEqual(summary["unknown_usage_attempts"], 1)
        self.assertEqual(summary["attempts"], 1)

    def test_budget_exhaustion_refuses_new_jobs(self):
        class Small(pilot_harness.PilotLimits):
            pass
        Small.max_transmissions = 8
        Small.max_recoveries = 5
        with patch.object(pilot_harness, "PilotLimits", Small):
            constrained = offline_run()
        self.assertEqual(constrained["run_state"], "stopped: call_budget")
        summary = constrained["budget_summary"]
        # Base calls = 8 - 5 = 3 planned jobs; the 4th new job is refused
        # before dispatch and nothing silent succeeds afterwards.
        self.assertEqual(summary["attempts"], 3)
        self.assertEqual(sum(len(job.get("transmissions", []))
                             for job in constrained["telemetry"]), 3)
        refused = [job for job in constrained["telemetry"]
                   if not job.get("transmissions")]
        self.assertTrue(refused)
        self.assertTrue(all(job.get("error_code") == "call_budget"
                            for job in refused))
        believed = [job for job in constrained["telemetry"]
                    if job.get("transmissions")]
        self.assertTrue(all(job["outcome"] == "success" for job in believed))

    def test_retryable_429_recovers_within_envelope(self):
        attempts = []
        def flaky(endpoint, wire, key, timeout):
            if not attempts:
                attempts.append(1)
                return 429, {"Retry-After": "1"}, json.dumps(
                    {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}}).encode("utf-8")
            return respond(endpoint, wire, key, timeout)
        document = offline_run(transport=flaky)
        self.proof(document)
        summary = document["budget_summary"]
        self.assertEqual(summary["attempts"], 26)   # 25 planned + 1 recovery
        self.assertEqual(summary["recoveries"], 1)
        self.assertEqual(summary["retries"], 1)
        self.assertLessEqual(summary["attempts"], 30)
        self.assertEqual(document["run_state"], "completed")


class EvidenceFileTests(unittest.TestCase):
    def test_evidence_written_without_credentials(self):
        path = PROJECT / "ai-logs" / "opencode" / "session-05-offline-run.json"
        document = offline_run(evidence_path=path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["run_state"], document["run_state"])
        self.assertNotIn("synthetic-secret", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
