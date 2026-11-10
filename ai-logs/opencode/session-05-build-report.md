# Session 05 build report — H1 gates closure (offline verification complete)

Date: 2026-11-08. Model: `glm-5.3-flash-free` (OpenCode), Build mode.
Architecture: fixed Session 02 blueprint; Session 05 closure plan; no replanning.

## Files changed / created

| File | Change |
|---|---|
| `llm.py` | `temperature` default changed `0` → `None` (Option B, approved): `None` omits the field from the wire body (Gemini 3+ deprecation guidance); explicit finite numbers are validated and sent unchanged. Applies to `Client.chat`, `Client.request`, module-level `chat`. |
| `tests/test_llm.py` | Signature test updated to the new approved default; new regression `test_default_temperature_omitted_explicit_sent` proving both behaviors. |
| `tests/pilot_runner.py` | NEW — test-only bounded pilot runner over the Session 04 harness + mock + synthetic fixtures. Approved allocation lands at exactly 25 planned base dispatches (EX-8, ORG-2, ENT-3, GOALS-2, TASK-7 = interpret 7 + match 2, HELP-1); `VERIFIED_PRICING` projection embedded; `run_pilot(mode=…)` fails closed in real mode. |
| `tests/test_pilot_runner.py` | NEW — 13 offline tests: plan totals, bookkeeping/telemetry, explicit failure recording, determinism, safe-stop (`unknown_usage`, `call_budget`, failed-closed real mode), retryable-429 recovery, evidence-file write. |
| `ai-logs/opencode/session-05-offline-run.json` | NEW — genuine offline evidence (written by the tests). |
| `ai-logs/opencode/session-05-linux-acceptance-ubuntu.json` | NEW — fresh Linux acceptance result (see below). |
| `ai-logs/opencode/session-05-export.json`, `session-05-transcript.md` | NEW — genuine raw session export + rendered transcript (includes the model-token-exhaustion interruption and its resumption; nothing fabricated). |

## Test results

- Windows CPython 3.12.9, `python -B -m unittest discover -s tests`: **285 tests OK, exit 0**
  (271 prior + 1 new temperature regression + 13 new pilot-runner tests).
- Ubuntu WSL CPython 3.9.25, same suite: **285 tests OK** (one fix applied after the
  first 3.9 run: `Path.write_text(newline=)` is 3.10+; replaced with
  `path.open(..., newline=)` — portable to both versions, disclosed here).
- One 3.9-suite failure occurred before that fix; it is recorded in the
  transcript (genuine history).

## Offline pilot verification (fixtures only — no network, no credentials)

Evidence: `session-05-offline-run.json` — `run_state: completed`,
`attempt: 25 / 25 planned`, recoveries 0, retries 0, charged tokens 151,050 < 250,000,
projected USD 0.338 ≤ 2.00 ceiling, `envelope_verified: true`, `synthetic_only: true`.
Telemetry: 25 jobs, exactly one instrumentation per dispatch across all stages.

Stage states (offline mock, disclosed limitations included):

- ORG (EN, BN), GOALS (EN, HI), tasks all four packs: `succeeded`.
- ENT (EN, HI, BN): `incomplete`, 1 explicit failure each — the deterministic
  mock's routing tables cite C_PAIR/C_QUOTE scenes the scoped plan deliberately
  does not extract. Bookkeeping unaffected; a real model can complete these
  stages contractually.
- HELP (EN): `incomplete` — help candidate must pass full five-array coverage;
  offline scoped extraction cannot satisfy it. Explicitly recorded, no fabrication.

Dataset integrity: `data/dev` (`C:\…\Xpert\xpert-cold-start\data\dev`) SHA-256
re-verified against `session-03-workload-estimate.json` — all three files
identical (chats `e14372d5…`, messages `97493ce8…`, seed `93ebe3c1…`).

## Linux acceptance (Gate 4) — fresh run

`wsl -d Ubuntu` (WSL2, Ubuntu 26.04.1) with the existing uv CPython **3.9.25**
`/home/shalu_chauhan/.local/share/uv/python/cpython-3.9.25-linux-x86_64-gnu/bin/python3.9`:

`python3.9 -B -S tests/linux_acceptance.py --report ai-logs/opencode/session-05-linux-acceptance-ubuntu.json`

**Result: PASS — 10/10 cases** (hang, slow, stall, retry, crash, invalid,
ignore_term, launcher_hang, launcher_success, interrupted_write). Note: an
earlier attempt under `python3` (3.14.4) produced a genuine `BLOCKED` report in
the same file, which was then superseded by this PASS run; both attempts are in
the transcript. Note: Ubuntu 26.04 does not package 3.9.25 (its `python3` is
3.14.4); the suite ran against the existing uv-managed interpreter, newly
installed for this project, on this machine.

## Gate status

1,2,3,5 (already PASS): unchanged, evidence preserved.
Gate 4 — Linux acceptance: **now PASS** (fresh 10/10, CPython 3.9.25, run today).
Gate 6 — pilot runner + offline tests: **PASS** (this report + evidence JSON).
Gate 7 — real-output semantic review: **BLOCKED** (requires live pilot).
Gate 8 — cost/time forecast: **BLOCKED** (requires live pilot actuals).
Gate 9 — approval/signoff doc: **BLOCKED** (final consolidation).

## Exact next action — STOP; explicit user authorization required

No live API call has been made. The live pilot starts only after you confirm:

1. AI Studio free tier verified by you (no billing linked, quota adequate).
2. You supply runtime credentials (env: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`
   = Gemini 3.8 Flash endpoint/model); nothing is hardcoded.
3. Explicit "run the pilot" authorization, acknowledging the USD 2.00
   conservative ceiling as a projection (free tier actual = USD 0.00).

Then: live pilot (25 planned + ≤ 5 recoveries inside 30 transmissions / 250k
tokens / 600 s / USD 2.00) → Gate 7 semantic review against
`expected_matrix.json` → Gate 8 forecast → Gate 9 approval doc → final report.

## Limitations / disclosures

- Offline ENT/HELP incompleteness is a known mock-routing artifact, not a
  production-stage defect; it is recorded explicitly in the evidence file.
- The `temperature` default change touches the source signature asserted by an
  existing test (updated with a new bisecting regression test); it is contained
  to that one disclosed category.
- Transcript capture boundary: the raw export was refreshed after the final
  build actions; the complete final response is not inside it (same disclosed
  boundary as Sessions 02/03). The interruption and resumption are fully included.
- `ai-logs/opencode/INDEX.md` still ends at the Session 03 section (Session 04
  never updated it); left untouched — not a Session 05 task.
