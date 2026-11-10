# OpenCode session archive index — `ai-logs/opencode/`

Read-only companion records of the actual OpenCode work sessions, kept beside
the Codex records in `ai-logs/codex/`. Created from the running OpenCode 2.2.5
service via `GET /api/experimental/session/{sessionID}/export` (raw JSON,
byte-unmodified) plus deterministic Markdown renderings. Hidden model
reasoning, synthetic harness records and provider internals are excluded from
the Markdown; every user message, assistant response, agent switch and tool
call with its true input/output/status/timings is included. Long tool payloads
carry explicit `[truncated by archiver: ...]` markers; the raw JSON is complete.

The OpenCode session store contains exactly two sessions for this project
(verified 2026-11-06 via `GET /api/session`; no other session exists):

| Session (ID) | Created (UTC) | Title | Archive files |
|---|---|---|---|
| 00 — Plan-mode diagnosis (`ses_e52e01d67ffeu9Cb3sEyBWIRiP`) | 2026-11-05 19:11:50 | launcher_hang acceptance failure diagnosis | `session-00-plan-export.json` (351,440 bytes raw), `session-00-plan-transcript.md` |
| 01/02 — Build session (`ses_e52dfae70ffe2kTxngyH7TDTD0`) | 2026-11-05 19:12:18 | launcher_hang acceptance root cause | `session-01-transcript.json` (609,456 bytes raw, pre-compaction snapshot), `session-01-transcript.md`; live continuation as Session 02: `session-02-h1-export.json` (raw), `session-02-h1-transcript.md` |

## Session 00 — Plan-mode launcher_hang diagnosis

- Final result in-session: full root-cause diagnosis and the proposed minimal
  `run.sh` fix (no files modified in Plan mode).
- Verification (from the archived export): 1 user prompt, 12 assistant
  messages, 18 tool parts (11 completed, 7 error), chronological order valid,
  11 reasoning parts excluded, complete final response present.

## Session 01 — approved `run.sh` fix, focused verification, first archival

- Work in-session: `run.sh` launcher fix; focused `launcher_hang`,
  `launcher_success`, `interrupted_write` verification (all PASS); report in
  `session-01-implementation.md`; checkpoint update.
- Verification: 3 user prompts, 36 assistant messages, 44 tool parts
  (37 completed, 7 error), 1 agent switch, chronological order valid.
- Known boundary, disclosed in the 2026-11-06 entry of
  `ai-logs/codex/progress-checkpoint.md`: this raw snapshot was captured by the
  live service **before that documentation turn's final response**, so that
  closing response is not included in this historical file. The later
  continuation (Session 02) covers the same session and includes all Session 01
  turns up to its own capture point; see below.

## Session 02 — the same live build session continued: H1 final closure

- Clarification from the live store: the H1 closure conversation continues
  `ses_e52dfae70ffe2kTxngyH7TDTD0` (the Session 01 build session); no third
  session exists in the store. Archived under `session-02-*` names for clarity.
- Work in-session (see `session-02-h1-final-report.md`): full Linux acceptance
  rerun (10/10 PASS), complete Ubuntu Python 3.9.25 unit suite (245 OK),
  production hash comparison, consolidated H1 report, these archives.
- Export snapshot: 4 user prompts, 104 assistant messages, 119 tool parts
  (110 completed, 9 error), 1 agent switch, 1 compaction record (annotated in
  the transcript), chronological order valid.

## Capture boundary on `session-02-*`

`session-02-h1-export.json` was taken while the final consolidation response
was still being produced, so **that final response is not in it**. The single
remaining archival action is a genuine post-response refresh of the same two
files, overwriting only these Session 02 snapshots (Session 00/01 records are
never touched). Refresh commands, to be run after the final response is
delivered, from `ai-logs/opencode/`:

```
cmd /c 'opencode api get "/api/experimental/session/ses_e52dfae70ffe2kTxngyH7TDTD0/export" > "session-02-h1-export.json"'
wsl.exe -e /home/shalu_chauhan/.local/share/uv/python/cpython-3.9-linux-x86_64-gnu/bin/python3.9 -B 'C:\Users\Shalu Chauhan\AppData\Local\Temp\opencode\export_to_markdown.py' '<repo>/ai-logs/opencode/session-02-h1-export.json' '<repo>/ai-logs/opencode/session-02-h1-transcript.md' 'OpenCode Session 02 (H1 final closure: full Linux acceptance, Ubuntu unit suite, records, archival)'
```

Transcripts are rendered by `export_to_markdown.py` (kept in
`C:\Users\Shalu Chauhan\AppData\Local\Temp\opencode\`; its deterministic
rendering rules are quoted in the transcript headers themselves). Historical
Codex archives in `ai-logs/codex/` are untouched.

## Session 03 — H1 closure plan build + read-only workload estimation

| Session | Created (UTC) | Archive files |
|---|---|---|
| 03 — H1 closure planning (`ses_e4b2b834effexhEi2s76nyjqys`) | 2026-11-07 | `session-03-export.json` (949,255 bytes raw), `session-03-transcript.md` (285,480 bytes), `session-03-workload-estimate.json`, `session-03-plan-execution.md` |

- Work in-session: comprehensive H1 closure plan (saved as
  `..\..\..\..\TEMP-session-03-H1-closure-plan.md` in the Xpert folder;
  Plan-mode copy exists at `C:\Users\Shalu Chauhan\.opencode\plan\`), then in
  Build mode the READ-ONLY workload estimation over the three approved inputs
  using the production `load_input`/`build_windows` (temp estimator script,
  outside the repo). Results: 138 chats / 286 people / 4,502 messages; 280
  windows; 100% primary coverage; ~18.9% context overhead; ~1.43MB estimated
  extraction wire; ≥14 entity target-batch calls; input SHA-256 unchanged
  before/after. No LLM call, no cost, no production change.
- Verification (renderer output): 6 user prompts, 28 assistant messages,
  33 completed tool parts (2 error), 23 reasoning parts excluded,
  chronological order monotonic: true.
- Capture boundary: export taken while the final Session-03 response was still
  being produced — the complete final response is not yet in it. Genuine
  post-response refresh of `session-03-export.json` + `session-03-transcript.md`
  (these two files only) is the disclosed remaining archival action.

## Session 07 — pilot preflight + final model switch (`ses_e451f3c10ffevv4SLxROhjwYJp`)

| Session | Created (UTC) | Archive files |
|---|---|---|
| 07 — "Gemini pilot preflight checks" (`ses_e451f3c10ffevv4SLxROhjwYJp`) | 2026-11-08 | `session-07-export.json` (raw), `session-07-transcript.md`, `session-07-export.py` |

- Work in-session: read-only preflight (encoded request sizes for the 8 planned
  extraction windows via production packet builders; 25-base allocation and
  30-transmission envelope verification; gate 6/7/8 numbering reconciliation;
  blockers list), then the approved Build turn: pilot model switched to
  `gemini-3.5-flash-lite`, `VERIFIED_PRICING` refreshed to the official $0.30 /
  $2.50 Standard rates (retrieved 2026-11-08), temperature-omission regression
  moved to the new model, full offline suite 285 OK, WRITEUP/checkpoint updated.
- Raw + transcript rendered by `session-07-export.py` from the local OpenCode
  SQLite store (`session_message` rows), same exclusion/redaction/truncation
  rules as Session 06 (visible user/assistant messages, agent switches and tool
  calls kept; hidden reasoning, synthetic harness records, idle bookkeeping
  excluded from Markdown only).
- Capture boundary: the exporter re-runs at the very end of the session, so
  everything up to that moment — including the final PowerShell command — is
  included; the closing turn and the export itself postdate their own capture.
  Re-run `session-07-export.py` for a final byte-faithful refresh. Earlier
  session archive files are never touched.

## Session 08 — model-switch re-verification + final build-session closure (`ses_e43a362cbffepcSxbg3AicXOd0`)

| Session | Created (UTC) | Archive files |
|---|---|---|
| 08 — "Session 08 Gemini Flash-Lite pilot preparation" (`ses_e43a362cbffepcSxbg3AicXOd0`) | 2026-11-08 | `session-08-export.json` (raw), `session-08-transcript.md`, `session-08-export.py` |

- Work in-session (single Build session, no Plan cycle): independent
  re-verification of the pilot model against Google's official documentation
  (pricing page, `gemini-3.5-flash-lite` model page, rate-limits page,
  what's-new API-changes section): exact stable model code confirmed, Free
  tier free-of-charge input/output, structured output supported, Standard paid
  rates $0.30/$2.50 per Mtok confirmed unchanged, `temperature` deprecated and
  ignored — client omission confirmed correct. Reservation addition: Free-tier
  context caching unavailable (unused by the pilot); the rate-limits page now
  defers per-model Free-tier quotas to AI Studio, so the recorded planning
  quotas (15 RPM / 250K TPM / 500 RPD) remain the working assumption with
  429/Retry-After backoff absorbing throttling either way. `VERIFIED_PRICING`
  gains a `verification` documentation block; approved pilot design unchanged
  (25 base / 5 recoveries / 30 transmissions / 250,000 tokens / 600 s / USD 2
  safeguard / four synthetic packs); pilot evidence path moves to
  `ai-logs/opencode/session-08-gate-6-pilot-evidence.json`. No live API call.
- Verification: full offline suite 285 tests OK (8.916s, exit 0); pilot-runner
  13 OK, pilot-harness 14 OK, test_llm 57 OK (temperature regression included);
  plan allocation probe: 25 planned base calls, envelope constants unchanged,
  four packs on disk, normalized pricing passes fail-closed checks.
- Raw + transcript rendered by `session-08-export.py` from the local OpenCode
  SQLite store, same exclusion/redaction/truncation rules as Session 07.
- Capture boundary: the exporter runs as the final tool call of the session;
  the closing response and the export postdate their own capture unless
  re-run. Sessions 00–07 archive files are never touched.

### Final PowerShell command (approved in-session; run manually by the user)

```powershell
cd 'C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert\xpert-cold-start-starter\cold-start'

$env:LLM_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/'
$env:LLM_API_KEY  = '<paste your Gemini API key here>'
$env:LLM_MODEL    = 'gemini-3.5-flash-lite'

@'
import json, sys
from pathlib import Path
PROJECT = Path(r"C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert\xpert-cold-start-starter\cold-start")
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT / "tests"))
from pilot_runner import run_pilot, VERIFIED_PRICING
doc = run_pilot(mode="real",
                verified_pricing=VERIFIED_PRICING,
                provider_controls_confirmed=True,
                evidence_path=str(PROJECT / "ai-logs" / "opencode" / "session-08-gate-6-pilot-evidence.json"))
print(json.dumps({k: doc[k] for k in
    ("run_state", "stopped", "error_code", "mode", "planned", "envelope_verified",
     "synthetic_only") if k in doc}, indent=1))
print("budget_summary:", json.dumps(doc.get("budget_summary"), indent=1))
'@ | python -B -S -
```

The key is typed only in the user's own PowerShell session; it is never
requested, printed, logged or committed by any script here.

### Session 08 conclusion — stdin-launch failure diagnosed; real-file launcher correction (2026-11-09)

The user ran the Session 08 command manually on 2026-11-08 19:55Z. **The run
failed harmlessly before any network dispatch**: the piped-stdin main module
could not be re-imported by Windows multiprocessing spawn children
(`_fixup_main_from_path('<stdin>') -> OSError [Errno 22]`, repeated 13 times),
so all 13 spawned HTTP workers died with exitcode 1 and every transmission
recorded `worker_failure`; zero Gemini API requests were sent, zero token
usage or spend occurred. The pilot envelope itself behaved exactly as
designed: 8 extraction jobs dispatched, 13 transmissions (8 originals + 5
recoveries), 25 planned dispatch causes accounted, every downstream stage
recorded explicit `incomplete` states without fabricated output,
`envelope_verified: true`, all who `unknown_usage` reservations retained
conservatively. Run-state diagnostics were reproduced offline by the agent
(stdin probe → child exit 1 with identical Errno 22; real-file probe → child
exit 0).

Failure evidence preserved unchanged, SHA-256 verified before/after copy:
`session-08-gate-6-pilot-evidence.json` →
**`session-08-gate-6-stdin-launch-failure-evidence.json`** (SHA-256
`3d79bc1e1a75d57eeb787950143540f43f6e976f6299ef8ed2e75cea2ba6829e`).

Launcher correction (smallest change; production pilot architecture and all
approved envelope limits unchanged — 25 base / 5 recoveries / 30
transmissions / 250,000 tokens / 600 s / USD 2.00 safeguard / four synthetic
packs):
- New `pilot_launch.py` (project root): `if __name__ == "__main__":` guard so
  spawned children re-import the module inertly; reads `LLM_BASE_URL`,
  `LLM_API_KEY`, `LLM_MODEL` from the inherited environment with
  presence-only checks (no value ever printed); requires exactly
  `gemini-3.5-flash-lite`; passes the official `VERIFIED_PRICING` and
  `provider_controls_confirmed=True` (standing Free-Tier/no-billing
  attestation) to the unchanged `run_pilot`, writing evidence to
  `ai-logs/opencode/session-08-gate-6-pilot-evidence.json`.
- `python -B .\pilot_launch.py --spawn-check`: harmless offline verification
  with no real dispatch - trivial module-level child (exitcode 0) plus the
  production `ProcessTransport` against a reserved `.invalid` endpoint with a
  synthetic non-credential; the child executed the real worker path and
  returned the structured `network` error over IPC (`start`/`reaped` events,
  `spawn_from_real_file_ok: true`).
- New `tests/test_pilot_launch.py`: 4 focused tests (environment refusal
  without dispatch or output leakage, exact-model refusal, pass-through with
  verified pricing, real-file spawn regression). Online result: 4 OK.
- Full suite after the correction: **289 tests, OK, 14.113s, exit 0**
  (Windows 11 / CPython 3.12.9).
- The historical PowerShell command above is SUPERSEDED (its heredoc-to-stdin
  form caused the failure); do not run it. The exact corrected command:

```powershell
cd 'C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert\xpert-cold-start-starter\cold-start'

$env:LLM_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/'
$env:LLM_API_KEY  = '<paste your Gemini API key here>'
$env:LLM_MODEL    = 'gemini-3.5-flash-lite'

python -B .\pilot_launch.py
```

Optionally first, offline and credential-free:
`python -B .\pilot_launch.py --spawn-check`.

### Session 08 conclusion — extraction quality correction after the first real run (2026-11-09)

The user ran the corrected launcher manually on 2026-11-08 20:16Z. Windows
spawn worked: 8 real Gemini extraction transmissions on
`gemini-3.5-flash-lite`, 14,650 reported tokens, zero unknown usage,
`envelope_verified: true`. Outcome: 2 extraction jobs succeeded (the four
packs' window-1 jobs of pilot_hi/pilot_hn), 4 jobs truncated — every window-0
job cut at completion 2044 against the 2048 wire cap (`finish_reason
"length"`) — and 2 window-1 jobs (pilot_en, 84 completion tokens; pilot_bn,
177) were valid-JSON finish-stop responses rejected by
`reasoning.validate_extraction` on the strict order/content form of the
`covered` list. All downstream stages stayed explicitly `incomplete` with no
fabricated output. Evidence:
`session-08-gate-6-pilot-evidence.json`, archived unchanged (SHA-256
`1079ac05c0724844b78fae76a9135dd06089f65457959e6d170ac8a499d3bd5e`) as
`session-08-gate-6-real-launch-partial-run-evidence.json`.

Smallest corrections, approved architecture/envelope unchanged:
- Pilot extraction wire cap 2048 → 4096 (`tests/pilot_runner.py`,
  `_dispatch_window`; production `extract_windows` default stays 2048) so
  full-window extractions can finish; verified before the change that the
  full 25-job schedule still fits the 250,000-token reservation under the
  new cap (extraction base 58,392; absolute worst 149,432; USD bound on all
  250k at output rate $0.625 < $2.00 safeguard).
- `reasoning.validate_extraction`: `covered` compared as an exact
  order-insensitive multiset (packet-echo extra keys ignored; int-valued
  string/float offsets coerced, including evidence items, which are
  normalized for downstream). Containment and byte-exact text checks are
  unchanged, so duplicates, partial coverage, wrong or out-of-span evidence
  remain rejected. `EXTRACTION_PROMPT` restates the three-key covered shape
  and original-body character offsets.
- `_dispatch_window` now records the REAL failure codes (`truncated`,
  `validation`, …) in telemetry instead of generic `request_failed`.
- Next-run evidence target is the NEW
  `ai-logs/opencode/session-08-gate-6-pilot-retry-evidence.json`
  (`pilot_launch.py EVIDENCE_PATH`); no evidence is ever overwritten.

New regression tests `tests/test_extraction_quality.py` (11), including
offline reproductions of both failure classes over the synthetic fixtures:
real codes surfaced, one transmission per failed job, zero recoveries, all
downstream stages explicitly incomplete with nothing dispatched on invented
observations, and the corrected 4096 cap on every extraction wire request.

Verification: focused file 11 OK; full suite `python -B -m unittest discover
-s tests -v` → **300 tests, OK, 20.930s, exit 0** (Windows 11 / CPython
3.12.9). One relaxation bug (sorted-expected vs packet-ordered covered) was
caught by the full suite breaking offline pilot_hi/bn/hn pipelines and
corrected by sorting both sides with one key.

Corrected command for the next bounded live attempt:

```powershell
cd 'C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert\xpert-cold-start-starter\cold-start'

$env:LLM_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/'
$env:LLM_API_KEY  = '<paste your Gemini API key here>'
$env:LLM_MODEL    = 'gemini-3.5-flash-lite'

python -B .\pilot_launch.py
```

### Session 08 conclusion - real retry run, downstream diagnosis, and honest corrections (2026-11-09)

The user ran `python -B .\pilot_launch.py` (corrected real-file launcher) and
the run wrote `session-08-gate-6-pilot-retry-evidence.json` (created
2026-11-09T06:10:59Z; PRESERVED, never overwritten). Real results on
`gemini-3.5-flash-lite` (Free tier): run_state `completed`,
`envelope_verified: true`, planned 25, dispatched 20 jobs over 21
transmissions (1 retry + 1 recovery), charged 35,372 tokens with 3,987
conservatively reserved for the one unknown-usage attempt, elapsed 73.657 s
of 600 s, projected USD 0.203 of the 2.00 internal safeguard, synthetic-only
confirmed. ALL 8 extraction windows succeeded.

Downstream outcome: 9 of 12 dispatched downstream jobs failed - 5x
`validation` (en organisations; hi entities; bn entities; en task-review x2)
and 4x `malformed_content` (en task-review x1; hi goals; hn task-review; bn
task-review, whose attempt 1 was a transient HTTP error and whose recovery
worked exactly as designed). 3 downstream successes: pilot_bn organisations
(a VALID empty envelope), pilot_en goals, pilot_hi task-interpret with one
honest unresolved item. 5 of the 25 planned jobs were correctly NOT
dispatched because prerequisites stayed incomplete (en entities gated by the
en organisations failure; en help - no open tasks after all interpretations
failed, so the invalid five-array candidate was recorded WITHOUT a help
dispatch; en/hn task match - no successfully interpreted events; one hn task
interpretation - interpretation is observation-driven and the real
extraction produced one sampled observation; offline plan counts are
estimates, telemetry records actuals).

Diagnosis limitation (disclosed, not reconstructed): pilot evidence does not
retain response bodies, so the exact `validation` deviations and the
Bengali HTTP status were unrecoverable from the existing run; the
`malformed_content` failures are attributable (finish-stop content failing
the strict JSON-object parse under `response_format json_object`), which
motivated only the parsing recovery below.

Smallest corrections shipped (approved architecture, module boundaries,
model, 25-request allocation and all envelope limits unchanged):
- `validation.py` + `llm.py`: one shared strict-first JSON reader
  (`read_json`) that, only when the strict parse fails, unwraps ONE balanced
  outermost {...} from fences/prose (string-aware scanner) and re-parses it
  under the SAME strict rules (duplicate keys, non-finite constants,
  non-object payloads still rejected); `Client._validate` now uses it, and
  `validation` failure details name the local exception class only. New
  acyclic `llm -> validation` import edge (validation.py is stdlib-only).
- `Budget.settle` records an integer-only `http_status` per transmission,
  and `tests/pilot_runner.py` carries it into job telemetry together with
  the safe local `error_detail` (closing the Bengali-run status loss for
  future runs).
- `reasoning.py`: raw-JSON-only requirement lines in CONTEXT_PROMPT and the
  task-review prompt; `context-2` -> `context-3` and `task-review-1` ->
  `task-review-2` version bumps (no validator loosened anywhere).
- `pilot_launch.py`: target evidence moves to the NEW
  `session-08-gate-6-pilot-retry-2-evidence.json`; `launch()` refuses BEFORE
  any dispatch if the target evidence file already exists.

New offline regressions: `tests/test_stage_quality.py` (16 tests: JSON
tolerance and strictness incl. duplicate-key/NaN/non-object/prose-only
rejections and braces inside strings; client acceptance of fenced/wrapped
objects with non-objects still `malformed_content`; local-class-only
`validation` details; help-dependency fail-closed; full offline pilot runs
asserting 25-for-25 planned dispatch accounting and envelope verification,
a transient 500 with exactly one retry+recovery and per-transmission
HTTP-status 500, an all-malformed interpretation run (7 jobs, zero
retries/recoveries, no match dispatch, 4 incomplete task stages, en help
failure with no help dispatch) and an invalid organisation envelope that
gates en entities with zero dispatch; prompt/version bumps; valid and
invalid task-interpretation events) plus `tests/test_pilot_launch.py` (+1:
existing evidence target refuses the launch pre-dispatch with the file left
byte-identical and zero runs).

Verification: `python -B -m unittest tests.test_stage_quality -v` 16 OK;
full suite `python -B -m unittest discover -s tests -v` - **317 tests, OK,
17.307s, exit 0** (Windows 11 / CPython 3.12.9). `WRITEUP.md` refreshed with
only evidence-supported statements (still within two pages); checkpoint
appended. NO live API call was made in this Build session.

**Gate 6: NOT PASSED.** The envelope verified and synthetic-only holds, but
9 of 12 downstream dispatches failed and the two-window persisted-run
correctness has never been demonstrated end-to-end. Gate 7 is not ready for
full semantic review (only extraction-window real outputs exist; an
extraction-window review may proceed meanwhile). Next live run requires
separate explicit user authorization; the launcher now targets
`session-08-gate-6-pilot-retry-2-evidence.json` and can never overwrite the
preserved `session-08-gate-6-real-launch-partial-run-evidence.json` /
`session-08-gate-6-pilot-retry-evidence.json` evidence. Sessions 00-07 and
all prior evidence untouched.

### Session 08 conclusion - bounded privacy-safe response capture prepared for the next Gate 6 run (2026-11-09, second Build session)

Evidence preservation verified by SHA-256 before any work, files untouched:
`session-08-gate-6-stdin-launch-failure-evidence.json` (`3d79bc1e…ba6829e`),
`session-08-gate-6-real-launch-partial-run-evidence.json` (`1079ac05…d3bd5e`),
`session-08-gate-6-pilot-retry-evidence.json` (`0ce77f58…de5f48f`).

Capture seam shipped (minimal, opt-in, response-side only) so the next
bounded live run produces precisely diagnosable evidence and Gate 7 review
material:
- `llm.py`: opt-in `Client(capture=..., capture_max_bytes=4096)` records one
  bounded record per settled attempt: job identifier, allowlisted
  cache-context identifier fields, attempt/recovery/retry flags, settled
  outcome code, HTTP status, finish_reason, model, safe local `error_detail`,
  a byte-capped response body (exact uncapped byte length + SHA-256 of the
  uncapped response + `body_truncated`) and the capped extracted content.
  Provider error pages for non-2xx are NEVER captured. Never captured: the
  request/wire body, transport headers, endpoint, credentials, or anything
  original-challenge-shaped (inputs are the four synthetic packs only).
  Capture failures are counted, never fatal. Default off.
- `tests/pilot_harness.py` forwards the seam; `tests/pilot_runner.py`
  `run_pilot(..., capture_path=...)` writes a separate capture artifact with
  the same JSON guarantees, adds an additive `response_captures` summary to
  the evidence document, and refuses pre-dispatch when the target capture
  file exists or collides with the evidence path.
- `pilot_launch.py`: the approved launch now targets BOTH
  `session-08-gate-6-pilot-retry-2-evidence.json` AND
  `session-08-gate-6-pilot-retry-2-captures.json`, refusing before any
  dispatch when either file already exists. Preserved evidence can never be
  overwritten.

Observation-driven dispatch documented in the pilot runner: TASK-stage
planned counts are planning estimates; interpretation dispatches are the
task observations the REAL extraction produced for the sampled stable
message IDs, the runner never invents events to reach 25, and the real
retry run's 6-of-7 interpretations + no match/help dispatches were the
correct prerequisite-incomplete outcomes. No jobs or events were invented.

New offline regressions: `tests/test_response_capture.py` (14 tests:
default-off; success-field capture; request-side sentinel/key/endpoint/
headers never captured; strict byte cap keeping full uncapped SHA-256 and
byte length; malformed_content/validation outcome captures; HTTP error
pages uncaptured while status is recorded; retry flags; non-fatal capture
sink; cache-context allowlist; full offline mock run 25/25 captures with
artifact redaction, never-overwrite refusal, no-dispatch-on-refusal, and
path-collision refusal) plus `tests/test_pilot_launch.py` (+1: existing
captures target refuses the launch pre-dispatch; capture_path pass-through
asserted).

Verification: `python -B -m unittest tests.test_response_capture
tests.test_pilot_launch` 16 OK; full suite `python -B -m unittest discover
-s tests -v` - **332 tests, OK, 20.802s, exit 0** (Windows 11 /
CPython 3.12.9); Windows spawn check `python -B .\pilot_launch.py
--spawn-check` exit 0 (`spawn_from_real_file_ok: true`). No live API call.
WRITEUP.md refreshed within two pages (test count 332, capture rules,
corrected 9-of-20 statement); checkpoint appended; `WRITEUP`'s prior
7-of-20 failure statement was corrected to the evidence-supported 9 of 20.

**Gate 6: still NOT PASSED** (unchanged). Remaining blockers before it can
pass: one further bounded live run on the corrected code with the fresh
non-overwriting evidence + capture files (separate explicit user
authorization; not executed here), downstream stages finishing or honestly
failing-closed end-to-end, and then reconciliation of the new run against
the corrected behavior. Gate 7 semantic review becomes fully possible once
the captured structured responses exist for the extraction AND downstream
windows. H2 remains a separate future approval. Sessions 00-07 and all
prior evidence untouched.

## Session 09 — Targeted repair session: retry-2 diagnosis, launcher-test fix, contract corrections (2026-11-10)

Read-only repair session (OpenCode 2.2.5, this session; no live API call, no
development-dataset inference, no dependency changes). Backups: the full
production tree was verified byte-identical (MD5, every file) against
`C:\Users\Shalu Chauhan\AppData\Local\Temp\opencode\Xpert-Backup-20261110-190831\`
before any edit. All five preserved pilot-evidence/capture artifacts were
hash-verified untouched before and after the session (`stdin-launch`
3d79bc1e…, partial-run 1079ac05…, retry 0ce77f58…, retry-2 evidence
A062B220…, retry-2 captures A39A885C…, matching the earlier checks).

### 1. The repository contained an undocumented third real pilot run

`session-08-gate-6-pilot-retry-2-evidence.json` (created 2026-11-09T07:42Z)
and `...retry-2-captures.json` already existed: a completed, bounded,
synthetic-only real run (18 transmissions, 23,790 provider-reported + 44,523
conservatively reserved unknown-usage tokens, 68,313 charged, 3 recoveries,
including one real 503 → 1-recovery success, envelope verified, $0.20
paid-equivalent). Neither the checkpoint nor the INDEX recorded it — this
entry closes that disclosure gap. **Gate 6: NOT PASSED** by this run; 9
dispatched downstream/one-extraction failures remained.

### 2. Captured failure diagnosis (from the byte-capped response bodies)

- `extract:cb9459…:0` (pilot_en): three consecutive transient HTTP 503 —
  bounded retry/recovery worked exactly as designed; no code change needed.
- `extract:cb9459…:1` (pilot_en): a valid-JSON, finish-stop extraction whose
  observation put the organisation NAME `HomeServe` in `subjects` — unknown
  subject → fail closed. Prompt gap, now closed (see 3).
- `goals:fcce90…` (pilot_hi): otherwise-valid JSON with ONE unquoted key —
  `title:` missing its quotes under response_format json_object → correctly
  `malformed_content`; unrepairable without weakening parsing. Prompt gap.
- `entities:bc2979…`/`entities:0af5ff…` (pilot_hi/bn): decisions returned in
  the exact envelope BUT with FOUR echoed top-level schema keys
  (`people`, `organisations`, `chats`, `goals`, `open_loops`), plus in bn an
  evidenceless positive record (P04, `circle: "vendor"`) that correctly
  failed the evidence-requirement rule. Both systemic contract ambiguities.
- `task-review:072d03…` (pilot_bn): the event cited the observation's hash
  identifier in `evidence` instead of a message ID → fail closed.

### 3. Smallest reliable changes (no architecture change, no validator loosened)

- `reasoning.py`: `EXTRACTION_PROMPT` forbids names/organisation names in
  `subjects` (copy exact packet IDs; names belong in `meaning`) —
  `extract-1`→`extract-2`. `CONTEXT_PROMPT` gains envelope exclusivity
  ("never echo the supplied schema and never add top-level keys beyond the
  contract's named keys") and a double-quoted-JSON-keys requirement
  (no unquoted keys, single quotes, trailing commas) — `context-3`→
  `context-4`. Entity contract (entity-3 text) now requires nonempty
  evidence for every nonempty record unless the seed fixes its fields.
  Task-review prompt requires exactly message IDs from the packet in
  `evidence`, never observation/hash identifiers — `task-review-2`→
  `task-review-3`. No provider/model-specific logic added anywhere.
- `tests/test_pilot_launch.py`: `test_exact_model_launches_with_verified_
  pricing` now isolates BOTH launcher targets into a temporary directory
  (root cause of the pre-existing failure: preserved real retry-2 artifacts
  legitimately trigger `target_exists`, so `run_pilot` was never reached,
  `AssertionError: 0 != 1`). Production never-overwrite protection unchanged
  and verified: the two existing-refusal tests still pass, and the real
  files were not deleted or modified.
- New `tests/test_capture_regressions.py` (10 tests): each captured shape is
  replayed offline against the production validators — name-subject
  rejection + valid-ID control; unquoted-key content stays
  `malformed_content` (no parser repair); the echo envelope fails
  `resolve_entities` fail-closed while the envelope-only equivalent of the
  SAME decisions succeeds (anti-overfit control); observation-hash task
  evidence rejected with message-ID control; prompts asserted model-agnostic
  (no provider/model tokens).

### 4. Verification (this session, offline only)

- `python -B -m unittest discover -s tests -v` → **342 tests, OK, 9.858 s**,
  exit 0, Windows 11 / CPython 3.12.9 (was 332 with 1 failure).
- `python -B -S tests/offline_readiness.py` → all stages `succeeded`; sparse
  15,000-message fixture 3.659 s / 599 fake calls; dense 40.183 s / 765 fake
  calls; identical end-to-end output SHA-256 on both fixtures; Python 3.9
  grammar + import checks passed (post-edit module SHA-256 changes recorded
  in the machine output).
- `python -B data.py ..\..\xpert-cold-start\data\dev` metadata-only check
  unchanged: `succeeded`, 138 chats, 286 people, 4,502 messages, no issues.
- `python -B solution.py example out.json` with no environment configured →
  exit 1 fail-closed, no output file written.

### 5. Honest status

Gate 6: **NOT PASSED** and NOT claimed. The corrected prompts are an
evidence-based hypothesis validated offline as contract regressions only;
they have never run against a real model. No development-set evaluation
exists. A further authorized bounded live run (fresh non-overwriting
evidence/capture targets) is required before any Gate-6 or accuracy claim,
and H2/full-run approval remains separate. All prior session records are
preserved unchanged; this section and
`ai-logs/opencode/session-09-repair-session.md` are new additions.

## Session 10 — Corrected-prompt live validation run (2026-11-10)

User-authorized single live pilot on the Session-09 corrected code; the user
executed `pilot_launch.py` in their own terminal with a freshly rotated key
(no credential value printed/logged anywhere). Launcher support added first
(offline): optional `PILOT_EVIDENCE_PATH` + `PILOT_CAPTURES_PATH`
fresh-destination override, both-or-neither, never-overwrite refusal
re-applied to selected targets; defaults unchanged; 3 focused tests added
(`tests.test_pilot_launch` 9/9 OK; full suite **345 tests, OK**;
`--spawn-check` → `spawn_from_real_file_ok: true`). Pre-edit backup
verified byte-identical: `...\Temp\opencode\Xpert-Backup-20261110-192403\`.

The run (evidence `session-10-gate-6-validated-{evidence,captures}.json`,
created 2026-11-10T14:00:13Z; evidence SHA-256 42CB1DC752F41237…, captures
823A8EC9350A45D6…): 15/25 planned jobs dispatched; **20 transmissions (≤30),
5 recoveries (limit reached exactly), 59,672 charged tokens (≤250,000),
projected USD 0.2024 paid-equivalent (Free tier $0), 102.516 s elapsed
(≤600 s); envelope_verified true; synthetic_only true; run_state completed.**
Tokens: provider-reported 23,659 (13,913 prompt / 9,746 completion);
conservative reservation 77,446 prompt + 71,680 completion; 5 unknown-usage
attempts fully settled (36,013 reserved, 0 outstanding). Evidence/captures
relocated ONLY from project root into `ai-logs/opencode/` with SHA-256
verification (byte-identical; my path-handling comment caused the original
root placement).

Stage results: extraction 7/8 windows, en goals succeeded, bn organisations
succeeded_empty, bn entities SUCCEEDED with exactly `{decisions}` and
correct seed-exempt evidence, bn task-review succeeded (honest ambiguous),
hn tasks succeeded_empty; en organisations + en tasks (2 packets) failed
validation, en help invalid_candidate (previously disclosed), hi downstream
and en/hi entities never dispatched (honest prerequisite incompleteness).

Session-08 class verdicts: name-in-subjects RESOLVED; unquoted keys RESOLVED
(zero malformed_content); envelope echo RESOLVED on bn (inconclusive en/hi);
evidenceless positive records RESOLVED on bn (entity-3 followed exactly);
hash-as-evidence RESOLVED (all task evidence = message IDs); 503s recurred
5x, contained by bounded retry as designed (5/5 recoveries consumed).

Two NEW prompt-side contract gaps (both fail-closed, both validators correct):
the packet contracts do not enumerate the `organisations` record type
(company/residence/…; model said "organisation") or the task `details.type`
(commitment/followup/deadline/question; model said "task"/"request"); plus
one Hindi window failed strict evidence-text equality on a one-character
Indic transcription slip (दोपहर → दपोर). Full analysis:
`ai-logs/opencode/session-10-live-validation.md`.

**Gate 6: NOT PASSED** (documented criteria; no threshold changed) —
in-envelope and integrity pass; downstream did not finish or honestly
complete end-to-end (en stalled at organisations, hi at extraction; entities
evaluated only for bn). The corrected prompts demonstrably fixed the five
targeted content classes where they could execute, but the two new contract
gaps need a future user-authorized cycle (text/version bumps only, NO
validator loosening) before the next bounded run. H2/full-run/hidden-set
NOT STARTED. Sessions 00-09 and all prior evidence untouched (hashes
re-verified after the run).

## Session 11 — Targeted contract repair + offline verification (2026-11-10)

Offline-only repair of the two Session-10 contract gaps; **NO LIVE MODEL
CALLS MADE**. Pre-edit backup verified byte-identical:
`...\Temp\opencode\Xpert-Backup-20261110-195133\`. Session-10 captures
verified at `ai-logs/opencode/session-10-gate-6-validated-captures.json`
(SHA-256 823A8EC9…) before use.

Authoritative enumerations (schema.json, cross-checked with check.py):
- Organisations record: type ∈ [company, residence, vacation home,
  workspace, society, school, other]; side ∈ [home, work] (no null);
  role ∈ [owner, partner, helper, resident, parent, member, other].
- Task create details.type ∈ [commitment, followup, deadline, question].

Repairs (text + version bumps only; no validator/parser/schema/budget
change; provider-neutral):
- `reasoning.py`: the organisations packet contract documents all three
  record enumerations verbatim + "Never substitute an unlisted value or
  null for an enumerated field"; `CONTEXT_VERSION` context-4 → context-5;
  task-review-3 → task-review-4 prompt_version.
- `tasks.py`: task-review packet contract enumerates
  [commitment, followup, deadline, question] with "never substitute or
  invent another value".
- `tests/test_stage_quality.py` pins updated; new
  `tests/test_contract_enums.py` (16 tests): documentation equality with
  the schema (verbatim comma-joined enum lists), permitted-value success
  controls for both issues, captured-style and generic unsupported values
  fail-closed, message-ID evidence and unknown-owner rules intact, schema
  un-widened via the untouched SchemaValidator, provider-token-free text,
  consistent version bumps.

Verification (Windows 11 / CPython 3.12.9): full suite **361 tests, OK,
12.308 s** (345 + 16); `python -B -S tests/offline_readiness.py` → sparse
3.884 s/599 calls, dense 39.194 s/765 calls, both `succeeded`, identical
output SHA-256, python-3.9 grammar + imports passed; `python -B data.py
..\..\xpert-cold-start\data\dev` metadata smoke → succeeded, 138 chats,
286 people, 4,502 messages, no issues. All seven preserved evidence/
capture artifacts re-hashed unchanged after every edit (five Session-08 +
two Session-10). Full report:
`ai-logs/opencode/session-11-contract-repair.md`.

**Gate 6: remains NOT PASSED and is not claimed.** The enumeration fixes
have never run against a live model; the next bounded live validation (fresh
destinations via the launcher override) requires separate explicit user
authorization. H2/full-run/hidden-set NOT STARTED. Sessions 00-10 and all
prior evidence untouched.

## Session 12 — Second live validation of the Session-11 contracts (2026-11-10)

User-executed bounded live run (authorization action by running the
launcher); agent evaluation offline only. Run created 2026-11-10T14:35:40Z:
**11/25 planned jobs dispatched, 15 transmissions (≤30), 3 recoveries (≤5),
45,922 charged tokens (≤250,000), projected USD 0.1548 paid-equivalent
(Free $0), 80.374 s (≤600 s); envelope_verified, synthetic_only, completed.**
Provider-reported 19,005 tokens (10,024 prompt / 8,981 completion);
conservative reservation 55,036 + 55,296; 3 unknown-usage attempts settled
(26,917 reserved, 0 outstanding). Artifacts: the user's PILOT_* variables
reused the relative `session-10-gate-6-validated-*` names (root placement;
the preserved Session-10 originals in `ai-logs/opencode/` were untouched);
the NEW run's files were relocated byte-identically to
`ai-logs/opencode/session-12-gate-6-validated-{evidence,captures}.json`
(SHA-256 85643B8EA963B2DF… / 18250D938436B8D4…). Future runs need genuinely
fresh filenames (e.g. `session-13-*`).

Results: FIRST-EVER dispatch of the task-match and help stages; en task
create events ×2 succeeded with enumerated types (`followup`/`commitment`) —
**Issue B validated live**; extraction 4/7 windows (en:1, hi:5, bn:0
failed). Failures pinned: two strict-provenance rejections (en `HomeServe`
cited at wrong offsets 38:47 vs actual 51; hi `दोपहर`→`दपौर` transcription
slip, recurring); bn window-0 failure beyond the 4,096-byte capture cap
(honest inconclusive); task-match reply with EMPTY evidence for a `none`
decision rejected (validator requires the source message always cited —
**new prompt-side contract gap**, fix direction text + version bump in a
future authorized cycle); help reject of `remind_at:"1789635600Z"`
epoch-style (the prompt already documents ISO-with-offset — model
compliance failure, fail-closed correct). **Issue A (organisations enums)
NOT exercised live** — en organisations never dispatched (extraction
prerequisite failed).

**Gate 6: NOT PASSED** (documented criteria verbatim; no threshold changed)
— the pipeline went deeper than ever but did not honestly complete
end-to-end; organisations/entities were not exercised live this run. The
next bounded attempt is ready when authorized, using genuinely fresh
filenames. H2/full-run/hidden-set NOT STARTED. All prior evidence
untouched (hashes verified). Full report:
`ai-logs/opencode/session-12-live-validation.md`.
