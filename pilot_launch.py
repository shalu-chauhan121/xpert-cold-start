"""Session-08 real-file Windows launcher for the bounded Gate 6 pilot.

Corrects the stdin-launch failure of 2026-11-08: the previous Gate 6 command
piped the runner into `python -B -S -`, so Windows multiprocessing spawn
tried to reload `__main__` from a `<stdin>` path and every spawned HTTP
worker died before network dispatch (13 `worker_failure` transmissions, zero
live API calls, zero billed usage). The observed failure run is preserved at
`ai-logs/opencode/session-08-gate-6-stdin-launch-failure-evidence.json`.

Smallest correction, no production redesign: this standalone script runs the
EXISTING `tests/pilot_runner.run_pilot` and `VERIFIED_PRICING` interfaces,
whose real-mode `PilotHarness -> Client -> ProcessTransport` path is
unchanged, from a real .py file so spawn can re-import `__main__`.

Rules encoded here:
- `if __name__ == "__main__":` guard: spawned children re-import this module
  inertly (no nested pilot, no nested probes).
- `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL` come from the inherited
  environment. Presence is checked WITHOUT printing, echoing or logging any
  value. No credential-shaped string ever enters evidence or stdout here.
- `LLM_MODEL` must be EXACTLY `gemini-3.5-flash-lite` (stripped).
- Pricing: the official VERIFIED_PRICING table from `pilot_runner`
  (re-verified against Google documentation, 2026-11-08, Session 08).
- `provider_controls_confirmed=True` stands only on the user's existing
  Free-Tier, billing-not-enabled attestation (Session 07). No billing
  activation, no paid fallback.
- Under the user-approved pilot design: 25 base requests, max 5 recoveries,
  max 30 transmissions, 250,000 reserved tokens, 600 s network deadline,
  USD 2.00 internal paid-equivalent safeguard, four synthetic fixture packs
  only. Evidence is written to
  `ai-logs/opencode/session-08-gate-6-pilot-retry-2-evidence.json` and a
  separate bounded response-capture file to
  `ai-logs/opencode/session-08-gate-6-pilot-retry-2-captures.json`; the two
  prior real runs are preserved unchanged and never overwritten:
  `session-08-gate-6-real-launch-partial-run-evidence.json` (first real-file
  run: extraction-window failures) and
  `session-08-gate-6-pilot-retry-evidence.json` (full corrected retry: 21
  transmissions on 20 jobs, all 8 extractions succeeded, downstream
  `validation`/`malformed_content` failures diagnosed in Session 08). The
  launcher refuses to dispatch at all when either target file already
  exists, so preserved evidence can never be overwritten.

Response capture rules (Session-08 diagnostic addition): every settled
attempt records ONE bounded, response-side capture (structured response
bodies, stage/job identifiers, cache-context identifier fields, finish
reasons, HTTP status and local validation-outcome details), for Gate 7
semantic review and the precise diagnosis future `validation` vs
`malformed_content` run failures need. Strict per-response byte cap (4,096)
with exact uncapped byte length and SHA-256 retained. NEVER captured: API
keys, authorization headers, transport headers, request/wire bodies,
original challenge conversations (inputs are the four synthetic packs
only), and provider error pages for non-2xx responses.

`python -B pilot_launch.py --spawn-check` verifies Windows spawn from a real
launcher file WITHOUT any real dispatch: (1) a trivial module-level child;
(2) the production ProcessTransport against the reserved `.invalid` domain
with a synthetic non-credential, which can never reach any real endpoint.
The child then reports a structured `network` error through the real IPC
protocol - the exact distinction from the stdin failure (whose children
crashed with exitcode 1 and `worker_failure` before running the worker).
"""
import json
import multiprocessing
import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
TESTS = PROJECT / "tests"
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

PILOT_MODEL = "gemini-3.5-flash-lite"
REQUIRED_ENVIRONMENT = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
DEFAULT_EVIDENCE_PATH = (PROJECT / "ai-logs" / "opencode"
                         / "session-08-gate-6-pilot-retry-2-evidence.json")
DEFAULT_CAPTURES_PATH = (PROJECT / "ai-logs" / "opencode"
                         / "session-08-gate-6-pilot-retry-2-captures.json")
EVIDENCE_PATH = DEFAULT_EVIDENCE_PATH
CAPTURES_PATH = DEFAULT_CAPTURES_PATH


def resolve_targets(environ=None):
    """Session-10: optional fresh evidence/capture destinations.

    With BOTH `PILOT_EVIDENCE_PATH` and `PILOT_CAPTURES_PATH` set to
    nonempty values, the targets for this run become those paths
    (relative paths resolve against the project root); with neither set
    the defaults stay the preserved Session-08 retry-2 filenames exactly
    as before. Setting only one is a configuration refusal. The
    never-overwrite rule is unchanged and re-applies to whatever
    destinations are selected by `launch`, so preserved evidence is
    never overwritten under any configuration.
    """
    env = os.environ if environ is None else environ
    evidence = (env.get("PILOT_EVIDENCE_PATH") or "").strip()
    captures = (env.get("PILOT_CAPTURES_PATH") or "").strip()
    if bool(evidence) != bool(captures):
        return None, None, "configuration"
    if not evidence:
        return DEFAULT_EVIDENCE_PATH, DEFAULT_CAPTURES_PATH, None
    evidence_path = Path(evidence)
    captures_path = Path(captures)
    if not evidence_path.is_absolute():
        evidence_path = PROJECT / evidence_path
    if not captures_path.is_absolute():
        captures_path = PROJECT / captures_path
    return evidence_path, captures_path, None
SPAWN_CHECK_ENDPOINT = "https://pilot-spawn-check.invalid/v1/chat/completions"


def _probe_target():
    """Trivial module-level spawn target: actionable only by name."""
    return None


def credential_status():
    """Presence booleans only. Values are never read into output."""
    return {name: bool(os.environ.get(name, "").strip())
            for name in REQUIRED_ENVIRONMENT}


def refusal(stopped, message):
    return {"run_state": "refused", "stopped": stopped,
            "error_code": stopped, "message": message}


def launch(mode="real"):
    """Real-mode launch after local checks. Returns the pilot evidence.

    mode == "spawn-check" runs the two harm-probe variants only.
    Any refusal here happens BEFORE run_pilot is constructed, so the
    fail-closed gates in the harness and client stay authoritative.
    """
    if mode == "spawn-check":
        return run_spawn_check()
    missing = [name for name, present in credential_status().items()
               if not present]
    if missing:
        return refusal("configuration",
                       "Missing environment values (presence checked only, "
                       "never values): " + ", ".join(missing))
    model = os.environ["LLM_MODEL"].strip()
    if model != PILOT_MODEL:
        return refusal("configuration",
                       "This pilot requires exactly LLM_MODEL=" + PILOT_MODEL
                       + "; refusing any other configured identifier.")
    evidence_path, captures_path, target_error = resolve_targets()
    if target_error is not None:
        return refusal(target_error,
                       "Fresh destinations must set BOTH "
                       "PILOT_EVIDENCE_PATH and PILOT_CAPTURES_PATH "
                       "(or neither); one alone is refused.")
    if evidence_path.exists() or captures_path.exists():
        # Evidence and capture preservation are absolute: prior runs' files
        # are never overwritten, and no dispatch happens under an unsafe
        # evidence/capture plan (this refusal applies to the DEFAULT
        # targets and to any explicitly selected fresh destinations alike).
        existing = [path.name for path in (evidence_path, captures_path)
                    if path.exists()]
        return refusal("target_exists",
                       "Target file(s) already exist and are never "
                       "overwritten: " + ", ".join(existing))
    from pilot_runner import run_pilot, VERIFIED_PRICING
    document = run_pilot(mode="real", verified_pricing=VERIFIED_PRICING,
                         provider_controls_confirmed=True,
                         evidence_path=str(evidence_path),
                         capture_path=str(captures_path))
    summary = {key: document[key] for key in
               ("run_state", "stopped", "error_code", "mode", "planned",
                "envelope_verified", "synthetic_only") if key in document}
    print(json.dumps(summary, indent=1))
    print("budget_summary:", json.dumps(document.get("budget_summary"),
                                        indent=1))
    return document


def run_spawn_check():
    """Harmless Windows spawn verification from this real launcher file."""
    results = {}
    # (1) Plain module-level child: spawn can re-import a real launch file.
    context = multiprocessing.get_context("spawn")
    child = context.Process(target=_probe_target)
    child.daemon = True
    child.start()
    child.join()
    results["module_child_exitcode"] = child.exitcode

    # (2) Production ProcessTransport end-to-end, against a reserved-domain
    # endpoint that cannot exist, with a synthetic non-credential. A child
    # that RAN the worker returns the structured "network" error over the
    # shared IPC buffer; a child that died at spawn yields exitcode!=0 and
    # "worker_failure" instead. No real endpoint and no real key involved.
    import llm
    transport = llm.ProcessTransport()
    raised = None
    try:
        transport(SPAWN_CHECK_ENDPOINT,
                  json.dumps({"model": PILOT_MODEL,
                              "messages": [{"role": "user",
                                            "content": "spawn-check"}]}).encode("utf-8"),
                  "synthetic-not-a-real-credential", 30.0)
    except llm.LLMError as failure:
        raised = failure.detail.get("code")
    results["transport_events"] = [e["event"] for e in transport.events
                                   if isinstance(e, dict)]
    results["transport_error_code"] = raised
    results["child_executed_worker"] = (raised == "network"
                                        and "reaped" in results["transport_events"])
    results["spawn_from_real_file_ok"] = (results["module_child_exitcode"] == 0
                                          and results["child_executed_worker"])
    print(json.dumps(results, indent=1))
    return results


if __name__ == "__main__":
    launch("spawn-check" if "--spawn-check" in sys.argv[1:] else "real")
