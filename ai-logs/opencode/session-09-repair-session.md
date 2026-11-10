# Session 09 — Final Targeted Repair Session (2026-11-10)

**Operator/agent:** OpenCode 2.2.5 (user-directed repair session)
**Scope:** Highest-priority problems from the 2026-11-10 repository audit.
**Mode:** Offline only. No live API call, no development-dataset inference,
no answers access, no dependency changes, no architecture redesign.
**Project root:** `...\Xpert\xpert-cold-start-starter\cold-start` (not a Git repo).

## 0. Preservation first

- Full pre-edit backup (robocopy mirror of `cold-start` + the dev-data tree +
  challenge PDF + H1 plan): `C:\Users\Shalu Chauhan\AppData\Local\Temp\opencode\Xpert-Backup-20261110-190831\`,
  verified byte-identical afterwards (every file MD5-compared; missing=0,
  differences=0).
- All five preserved pilot artifacts hash-verified unchanged before and after
  this session (SHA-256, first 16 hex):
  - stdin-launch failure evidence `3d79bc1e1a75d57e…`
  - real-launch partial-run evidence `1079ac05c0724844…`
  - pilot-retry evidence `0ce77f58c10901f8…`
  - pilot-retry-2 evidence `a062b220fc904a8d…`
  - pilot-retry-2 captures `a39a885c53bcaada…`
- No prior session record was edited. INDEX.md received an appended Session 09
  section; this file and the checkpoint append are new.

## 1. Failing launcher test — root cause and fix

**Symptom:** `test_pilot_launch.RealLaunchPassThroughTests.
test_exact_model_launches_with_verified_pricing` asserted
`recorder.call_count == 1` but got `AssertionError: 0 != 1`; the launcher
refused pre-dispatch.

**Root cause:** Session 08's retry-2 run wrote REAL evidence and captures into
`ai-logs/opencode/session-08-gate-6-pilot-retry-2-{evidence,captures}.json`.
The production launcher's never-overwrite protection correctly sees
`target_exists` for the module-level `EVIDENCE_PATH`/`CAPTURES_PATH` on every
repository state and refuses before `run_pilot` is ever called — so the test,
which depended on repository state, could no longer exercise pass-through.

**Fix (test-only):** the test now redirects BOTH module targets to paths inside
a `tempfile.TemporaryDirectory()` and captures the patched path values while
the patch context is active (module attributes revert on context exit, which
was a second subtle defect in the original assertions). Assertions still
verify the intended contract: mode `real`, `verified_pricing` is
`pilot_runner.VERIFIED_PRICING`, `provider_controls_confirmed` is truthy, and
both isolated paths are passed through to `run_pilot`.

**Production protection untouched:** `EnvironmentGateTests.
test_completed_evidence_refuses_dispatch` and the captures-side
never-overwrite test still pass unchanged; the real evidence files were never
deleted, moved or modified.

## 2. Captured model-response failures (retry-2) — diagnosis

Source: `session-08-gate-6-pilot-retry-2-captures.json` (18 captures, byte-
capped response bodies with SHA-256, synthetic packs only).

| # | Job (lang) | Outcome | Root cause |
|---|---|---|---|
| 1 | `extract:cb9459…:0` (en) | validation after 3 attempts | 3× transient HTTP 503; bounded retry/recovery worked as designed. No defect. |
| 2 | `extract:cb9459…:1` (en) | validation (ReasoningError: Unknown observation subject) | Valid JSON put organisation NAME `"HomeServe"` into `subjects` (must be person/chat IDs from the packet). Prompt ambiguity. |
| 3 | `goals:fcce90…` (hi) | malformed_content | One unquoted JSON key (`title:`) inside an otherwise valid `json_object` reply. Unrepairable without weakening strict parsing — correctly fail-closed. Prompt ambiguity (keys are quoted in examples only). |
| 4 | `entities:bc2979…`/`entities:0af5ff…` (hi/bn) | validation | Exact `{decisions}` envelope returned BUT four/five extra top-level schema keys echoed (`people`, `organisations`, `chats`, `goals`, `open_loops`); bn additionally had a positive record (P04, `circle:"vendor"`) with empty `evidence`. Both systemic contract ambiguities. |
| 5 | `task-review:072d03…` (bn) | validation | Event `evidence` cited the observation's hash identifier instead of a message ID. Fails closed correctly; prompt did not state the allowed ID type. |

## 3. Fixes implemented (prompt/contract text + version bumps only)

All in `reasoning.py`; no parser, validator, retry budget or token budget
changed; nothing provider-specific:

- `EXTRACTION_VERSION` `extract-1` → **`extract-2`**: `subjects` must copy
  exact packet IDs (P07, C12, ME…); names/organisation names/invented
  identifiers forbidden there, names belong in `meaning`; empty `subjects`
  allowed when only a name is known.
- `CONTEXT_VERSION` `context-3` → **`context-4`**: envelope exclusivity
  ("never echo the supplied schema and never add top-level keys beyond the
  contract's named keys") and strict double-quoted JSON keys ("no unquoted
  keys, single quotes, comments or trailing commas").
- Entity contract (entity-3 text): every NONEMPTY `record` (not `{}`/null)
  requires nonempty `evidence`; only seed-fixed fields skip that rule.
- Task-review prompt `task-review-2` → **`task-review-3`**: every `evidence`
  element must be exactly a message ID present in the packet's supplied
  messages and observation evidence — never an observation ID, hash or
  invented identifier.

Fail-closed behavior verified unchanged by the new regressions: the malformed
and invalid captured shapes still produce the same failure codes offline
(`malformed_content`, `validation`, fail-closed `incomplete`).

## 4. Tests added / changed

- `tests/test_capture_regressions.py` — **new, 10 tests** replaying each
  captured shape offline against production validators, with anti-overfit
  controls (the envelope-ONLY equivalent of the same hi/bn decisions still
  succeeds; an ID-subject extraction still validates; a message-ID task
  citation still validates). Also asserts prompts contain no provider/model
  tokens (model-agnostic).
- `tests/test_pilot_launch.py` — launcher test fixed as in §1 (6 tests OK).
- `tests/test_stage_quality.py` — `PromptVersionsTests` re-pinned to
  `extract-2` / `context-4` / `task-review-3` + new contract-text assertions
  (16 tests OK).

## 5. Commands and actual results (this host: Windows 11, CPython 3.12.9)

- `python -B -m unittest discover -s tests -v` → **Ran 342 tests in 9.858 s,
  OK** (was 332 tests with 1 failure). Exit 0.
- `python -B -S tests/offline_readiness.py` → both fixtures `succeeded`:
  sparse 15,000-msg fixture 3.659 s, 599 fake calls, peak
  ~34.6 MB traced Python bytes; dense 40.183 s, 765 fake calls, ~71.4 MB;
  identical end-to-end output SHA-256 across sparse/dense; Python-3.9 grammar
  + import checks passed; `site_disabled: true`; no network, no challenge
  data.
- `python -B data.py ..\..\xpert-cold-start\data\dev` metadata-only check:
  `succeeded`, 138 chats, 286 people, 4,502 messages, no issues (unchanged;
  answers/ never opened).
- `python -B solution.py example out.json` with no environment → exit 1
  fail-closed, no output file.

Notes: PowerShell prints cosmetic `NativeCommandError` noise for every python
invocation (stderr redirection artifact); the authoritative lines are the
`Ran N tests` / `OK|FAILED` results above.

## 6. Honest limitations

- Gate 6: **NOT PASSED** and not claimed by this session.
- The corrected prompts (`extract-2`/`context-4`/`task-review-3`) are an
  evidence-based hypothesis; they have never run against a real model.
- There is exactly one remaining live-only unknown per failure class: whether
  a different OpenAI-compatible model follows these contracts. The
  implementation remains model-agnostic.
- No development-set evaluation exists this session; semantic recall/precision
  remain unmeasured until a live pilot + Gate 7 manual review.
- The repository is still not a Git repository (tracked as an audit gap;
  out of this session's scope).

## 7. What a next session would need (requires explicit authorization)

One further bounded live run on the corrected code, targeting FRESH
non-overwriting evidence/capture files (the launcher refuses the existing
retry-2 artifacts by design), then reconciliation of the run against the
corrected contracts before any Gate-6 claim.
