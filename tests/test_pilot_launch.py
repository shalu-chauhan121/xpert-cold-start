"""Session-08 focused tests for the real-file pilot launcher.

The launcher is a manual run envelope around the UNCHANGED
``pilot_runner.run_pilot``/``VERIFIED_PRICING`` interfaces; these tests cover
only the launcher-local gates: credential-presence refusal without printing
values, the exact-model requirement, the pass-through to run_pilot with the
official verified pricing, and Windows spawn from a real launcher .py file
(the regression for the Session-08 stdin failure: children must be able to
re-import ``__main__`` without an Errno 22).

Synthetic environment values only; recorder intercepts run_pilot, so no
network dispatch and no real credential are involved. Spawn children execute
trivial module-level targets and contain no networking.
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

import pilot_launch
import pilot_runner

SYNTHETIC_ENV = {"LLM_BASE_URL": "https://synthetic.invalid/v1/",
                 "LLM_MODEL": "gemini-3.5-flash-lite",
                 "LLM_API_KEY": "synthetic-never-a-real-key"}


def call_launch(env):
    """Run the launcher's real-mode entry with captured stdout."""
    captured = io.StringIO()
    with patch.dict(os.environ, env, clear=True), \
            redirect_stdout(captured):
        document = pilot_launch.launch("real")
    return document, captured.getvalue()


class EnvironmentGateTests(unittest.TestCase):
    def test_missing_environment_refuses_without_dispatch(self):
        calls = []
        with patch.object(pilot_runner, "run_pilot",
                          lambda *a, **k: calls.append((a, k))):
            document, out = call_launch(
                {"LLM_BASE_URL": "https://synthetic.invalid/v1/",
                 "LLM_API_KEY": "synthetic-never-a-real-key"})
        self.assertEqual(document["run_state"], "refused")
        self.assertEqual(document["error_code"], "configuration")
        self.assertIn("LLM_MODEL", document["message"])
        self.assertEqual(calls, [])
        self.assertFalse(out.strip())  # No stdout content, no values printed.

    def test_wrong_model_refuses_without_dispatch(self):
        calls = []
        env = dict(SYNTHETIC_ENV, LLM_MODEL="gemini-3.8-flash")
        with patch.object(pilot_runner, "run_pilot",
                          lambda *a, **k: calls.append((a, k))):
            document, out = call_launch(env)
        self.assertEqual(document["run_state"], "refused")
        self.assertEqual(document["error_code"], "configuration")
        self.assertIn("exactly", document["message"])
        self.assertEqual(calls, [])
        self.assertNotIn("synthetic-never-a-real-key", out)


class RealLaunchPassThroughTests(unittest.TestCase):
    def test_existing_captures_target_refuses_without_dispatch(self):
        """The bounded capture artifact gets the same never-overwrite rule."""
        import tempfile
        handle, existing = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        with open(existing, "w", encoding="utf-8") as fp:
            fp.write('{"prior": 1}\n')
        calls = []
        try:
            with patch.object(pilot_launch, "CAPTURES_PATH", Path(existing)), \
                    patch.object(pilot_runner, "run_pilot",
                                 lambda *a, **k: calls.append((a, k))), \
                    patch.dict(os.environ, SYNTHETIC_ENV, clear=True):
                document = pilot_launch.launch("real")
        finally:
            with open(existing, encoding="utf-8") as fp:
                payload = fp.read()
            os.unlink(existing)
        self.assertEqual(document["run_state"], "refused")
        self.assertEqual(document["error_code"], "target_exists")
        self.assertEqual(calls, [])
        self.assertEqual(payload, '{"prior": 1}\n')

    def test_existing_evidence_refuses_without_overwrite_or_dispatch(self):
        """A completed prior run's evidence file blocks dispatch entirely.

        Session-08 preservation rule: the 2026-11-08 partial run and the
        corrected retry evidence must never be rewritten, so the launcher
        fails closed before any dispatch when its target filename exists.
        """
        import tempfile
        handle, existing = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        with open(existing, "w", encoding="utf-8") as fp:
            fp.write('{"preserved": true}\n')
        calls = []
        try:
            with patch.object(pilot_launch, "EVIDENCE_PATH",
                              Path(existing)), \
                    patch.object(pilot_runner, "run_pilot",
                                 lambda *a, **k: calls.append((a, k))), \
                    patch.dict(os.environ, SYNTHETIC_ENV, clear=True):
                document = pilot_launch.launch("real")
        finally:
            with open(existing, encoding="utf-8") as fp:
                payload = fp.read()
            os.unlink(existing)
        self.assertEqual(document["run_state"], "refused")
        self.assertEqual(document["error_code"], "target_exists")
        self.assertIn("never", document["message"])
        self.assertNotIn(existing, document["message"])
        self.assertEqual(calls, [])
        self.assertEqual(payload, '{"preserved": true}\n')

    def test_exact_model_launches_with_verified_pricing(self):
        """Pass-through works ONLY against isolated, nonexistent targets.

        Session-08 final repair: the repository contains the REAL retry-2
        evidence and captures files preserved by the never-overwrite rule,
        which made the launcher correctly refuse pre-dispatch with
        `target_exists` and broke this earlier state-dependent test
        (run_pilot was never reached, call_count 0). Production protection
        is unchanged. Session-10 refinement: isolation now goes through
        the launcher's supported fresh-destination override
        (PILOT_EVIDENCE_PATH + PILOT_CAPTURES_PATH) instead of patching
        module attributes, so the test exercises the same gate a real fresh
        run uses.
        """
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            env = dict(SYNTHETIC_ENV,
                       PILOT_EVIDENCE_PATH=str(Path(folder) / "isolated-evidence.json"),
                       PILOT_CAPTURES_PATH=str(Path(folder) / "isolated-captures.json"))
            with patch.object(pilot_runner, "run_pilot") as recorder, \
                    patch.dict(os.environ, env, clear=True):
                recorder.return_value = {"run_state": "completed", "planned": 25,
                                         "envelope_verified": True}
                document = pilot_launch.launch("real")
                overridden = {
                    "evidence": str((Path(folder) / "isolated-evidence.json")),
                    "captures": str((Path(folder) / "isolated-captures.json"))}
        self.assertEqual(recorder.call_count, 1)
        kwargs = recorder.call_args.kwargs
        self.assertEqual(kwargs["mode"], "real")
        self.assertIs(kwargs["verified_pricing"],
                      pilot_runner.VERIFIED_PRICING)
        self.assertTrue(kwargs["provider_controls_confirmed"])
        self.assertEqual(kwargs["evidence_path"], overridden["evidence"])
        # The response-capture artifact rides along on the same launch.
        self.assertEqual(kwargs["capture_path"], overridden["captures"])
        # The refusal precedes dispatch; any dispatch refusal stays the
        # harness's own fail-closed contract (unchanged production path).
        # The child test below verifies the real-file spawn regression.

    def test_fresh_destination_override_requires_both_or_neither(self):
        calls = []
        with patch.object(pilot_runner, "run_pilot",
                          lambda *a, **k: calls.append((a, k))):
            document, out = call_launch(dict(
                SYNTHETIC_ENV,
                PILOT_EVIDENCE_PATH=str(PROJECT / "ai-logs" / "opencode"
                                        / "session-10-new-evidence.json")))
        self.assertEqual(document["run_state"], "refused")
        self.assertEqual(document["error_code"], "configuration")
        self.assertIn("BOTH", document["message"])
        self.assertEqual(calls, [])
        self.assertFalse(out.strip())

    def test_fresh_destination_existing_target_still_never_overwritten(self):
        """The never-overwrite refusal re-applies to selected fresh targets."""
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            evidence = Path(folder) / "occupied.json"
            evidence.write_text('{"preserved-by-user": true}\n',
                                encoding="utf-8")
            calls = []
            with patch.object(pilot_runner, "run_pilot",
                              lambda *a, **k: calls.append((a, k))):
                document, out = call_launch(dict(
                    SYNTHETIC_ENV,
                    PILOT_EVIDENCE_PATH=str(evidence),
                    PILOT_CAPTURES_PATH=str(Path(folder) / "fresh-captures.json")))
            self.assertEqual(document["run_state"], "refused")
            self.assertEqual(document["error_code"], "target_exists")
            self.assertIn("occupied.json", document["message"])
            self.assertEqual(calls, [])
            self.assertFalse(out.strip())
            # The occupied file is preserved byte-for-byte.
            self.assertEqual(evidence.read_text(encoding="utf-8"),
                             '{"preserved-by-user": true}\n')

    def test_fresh_destination_relative_paths_resolve_against_project(self):
        """Relative overrides resolve against the project root (run mocked;
        no evidence file is created by this test)."""
        name = "session-10-relative-resolution-probe.json"
        expected = str(PROJECT / name)
        calls = []
        with patch.object(pilot_runner, "run_pilot") as recorder, \
                patch.dict(os.environ,
                           dict(SYNTHETIC_ENV,
                                PILOT_EVIDENCE_PATH=name,
                                PILOT_CAPTURES_PATH=name.replace(
                                    "evidence", "captures")),
                           clear=True):
            recorder.return_value = {"run_state": "completed"}
            document = pilot_launch.launch("real")
        self.assertEqual(recorder.call_count, 1)
        self.assertEqual(recorder.call_args.kwargs["evidence_path"], expected)
        self.assertFalse(Path(expected).exists())

    def test_spawn_check_is_harmless_and_passes_from_real_file(self):
        captured = io.StringIO()
        with redirect_stdout(captured):
            results = pilot_launch.run_spawn_check()
        self.assertEqual(results["module_child_exitcode"], 0)
        self.assertIn("start", results["transport_events"])
        self.assertIn("reaped", results["transport_events"])
        self.assertEqual(results["transport_error_code"], "network")
        self.assertTrue(results["child_executed_worker"])
        self.assertTrue(results["spawn_from_real_file_ok"])
        # No real credential involved in the probe payload or output.
        self.assertNotIn("synthetic-never-a-real-key", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
