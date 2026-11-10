# Session 10 — Live Validation of the Corrected Prompts (2026-11-10)

**Operator/agent:** OpenCode 2.2.5 (user-directed live pilot per session
contract; the user executed the launcher in their own terminal with a freshly
rotated key; no credential value was ever printed, logged, or stored by any
agent-controlled process).
**Scope:** validate the Session-09 corrected prompt versions
(extract-2 / context-4 / entity-3 / task-review-3) against the four synthetic
pilot fixtures with the configured live model; decide Gate 6 against the
documented criteria. No budget changes, no dev-data access, no answer access.

## Preflight (offline)

- Prompt versions verified in `reasoning.py`: `EXTRACTION_VERSION="extract-2"`,
  `CONTEXT_VERSION="context-4"`, entity contract entity-3 including the
  "Every nonempty record (not {} or null) needs nonempty evidence" clause,
  task-review `prompt_version: "task-review-3"`.
- Gate 6 criteria read from `ai-logs/codex/progress-checkpoint.md` (bounded,
  in-envelope, synthetic-only run with the evidence envelope verified; all
  downstream stages finishing or honestly failing-closed end-to-end;
  reconciliation against the corrected behavior; Gate 7 separately approved).
- All five Session-08 evidence/capture artifacts hash-verified unchanged
  before AND after the run; fixture packs are exactly
  `pilot_en`, `pilot_hi`, `pilot_bn`, `pilot_hn` (synthetic);
  envelope limits: 25 base, ≤5 recoveries, ≤30 transmissions, ≤250,000
  reserved tokens, ≤600 s, ≤USD 2.00; model pinned to exactly
  `gemini-3.5-flash-lite` by the launcher.
- **Launcher limitation fixed (smallest change, protection-preserving):**
  the launcher hardcoded the evidence/capture targets to the preserved
  retry-2 filenames, so a fresh-filename run was impossible. Added an
  OPTIONAL override — `PILOT_EVIDENCE_PATH` + `PILOT_CAPTURES_PATH`
  (both-or-neither, else configuration refusal) — with the same
  never-overwrite refusal re-applied to selected targets. Defaults unchanged.
  Three focused tests added; `tests.test_pilot_launch` 9/9 OK;
  full suite **345 tests, OK**; `--spawn-check` →
  `spawn_from_real_file_ok: true`. Pre-edit backup (MD5-verified):
  `C:\Users\Shalu Chauhan\AppData\Local\Temp\opencode\Xpert-Backup-20261110-192403\`.

## The run (user-executed, 2026-11-10T14:00:13Z)

- Model: `gemini-3.5-flash-lite`; fixtures: the four synthetic packs only.
- 15 of 25 planned jobs dispatched; **20 transmissions** (≤30), **5
  recoveries** (recovery limit reached exactly), all bounded.
- Tokens: provider-reported 23,659 (13,913 prompt / 9,746 completion);
  conservative internal reservation estimated 77,446 prompt + 71,680
  completion; 5 unknown-usage attempts fully settled
  (`unknown_usage_reservations: 36,013`, `outstanding: 0`);
  charged_tokens **59,672** ≤ 250,000.
- Projected cost **USD 0.2024** paid-equivalent (Free tier actual: $0).
- Runtime 102.516 s network-deadline elapsed (≤600 s); `envelope_verified:
  true`; `synthetic_only: true`; `run_state: completed`; stopped: null.
- Evidence: `ai-logs/opencode/session-10-gate-6-validated-evidence.json`
  (SHA-256 42CB1DC752F41237…); captures:
  `ai-logs/opencode/session-10-gate-6-validated-captures.json`
  (823A8EC9350A45D6…; 20 captures, 0 capture failures). Both files are
  byte-identical to what the launcher wrote (verified around a location-only
  move from the project root into `ai-logs/opencode/`).

## Stage-by-stage results

| Stage | pilot_en | pilot_hi | pilot_bn | pilot_hn |
|---|---|---|---|---|
| extraction | succeeded (2/2 windows; window 0 after 2×503) | 1/2 (window 5 failed text-match) | succeeded (2/2; window 0 after 1×503) | succeeded (2/2) |
| organisations | validation failed (see below) | not dispatched (extraction incomplete) | succeeded_empty (valid empty envelope) | n/a |
| goals | succeeded | not dispatched (extraction incomplete) | n/a | n/a |
| entities | not dispatched (organisations incomplete) | not dispatched (extraction incomplete) | **succeeded** (exact `{decisions}` envelope) | n/a |
| tasks | 2/4 packets failed validation, 2 honest | not dispatched | succeeded (honest ambiguous) | succeeded_empty |
| help | invalid_candidate (previously disclosed scoped-extraction coverage limitation) | n/a | n/a | n/a |

7/8 extraction windows succeeded (was 8/8 in retry-2 for different pack
sizes). 11 of 15 dispatched jobs fully succeeded; 4 failed caller validation,
each fail-closed with no fabrication.

## Failure-class verdicts (Session-08 captured classes)

1. **Organisation name as subject (extract) — RESOLVED.** No occurrences; all
   parseable extraction captures use ID subjects only; the org name appears
   in the correct place (organisations `record.name`). The validator
   provably rejects the old shape (pinned regression).
2. **Unquoted JSON keys — RESOLVED.** Zero `malformed_content` outcomes in 20
   settled attempts; zero parse failures.
3. **Extra echoed top-level schema keys — RESOLVED on pilot_bn** (entities
   envelope is exactly `{"decisions": [...]}`; nothing echoed) — pilot_en/
   pilot_hi entities were never dispatched (prerequisites incomplete), so
   those locales stay inconclusive.
4. **Positive record without evidence — RESOLVED on pilot_bn.** The model
   followed entity-3 exactly: positive circles (spouse/staff/colleague) are
   seed-covered fields (evidence-exempt by the contract clause), unknown
   persons got `{}` records — nobody claimed 'vendor'-style data without
   evidence.
5. **Observation hash instead of message ID in tasks — RESOLVED.** Every
   task-review reply cites real message IDs (M1/M2, M14, M9). The two
   English task-review failures cite correct IDs and fail on a different
   clause (see below).
6. **Transient HTTP 503 — REPEATED, contained as designed.** Five 503s
   across three jobs; the bounded retry/recovery path absorbed all of them
   (recovery budget 5/5 fully consumed — borderline but inside the envelope;
   two jobs succeeded after 503s, the third failed later on content).

## New findings this run (previously unseen)

- **Undisclosed enumerations in packet contracts (2 failures, prompt-side):**
  the organisations packet contract states `record:{name,type,side,role}`
  without the allowed values — the model answered `type:"organisation"`,
  rejected: schema requires one of (company, residence, vacation home,
  workspace, society, school, other). The task-review contract states
  `details:{}` with `type` required but lists no values — the model answered
  `"task"` / `"request"`, rejected: schema requires one of (commitment,
  followup, deadline, question). Same ambiguity family as the Session-09
  envelope class; validators are correctly fail-closed; the fix is contract
  text with version bumps (NOT validator loosening) in a future cycle.
- **Indic transcription slip (1 failure):** pilot_hi window 5 evidence text
  was 55 chars vs the 56-char source body — `दोपहर` transcribed as `दपोर`
  (one matra changed, one consonant dropped mid-word); strict evidence-text
  equality rejected it ("does not match original source"). Working as
  designed; unknown recurrence risk for non-Latin scripts.
- en help `invalid_candidate` — pre-existing, documented limitation of
  scoped extraction coverage; unchanged, unchanged disclosure.

## Gate 6 verdict: **NOT PASSED**

Documented criteria: bounded in-envelope synthetic-only run ✓ (all envelope
metrics within limits; envelope_verified true); evidence integrity ✓; BUT the
remaining mandatory condition — downstream stages finishing or honestly
failing-closed END-TO-END with reconciliation of the run against the
corrected behavior — is only partially met: pilot_en cannot proceed past
organisations, pilot_hi past extraction, and entities were evaluated only for
pilot_bn. The corrected prompts demonstrably fixed all five content classes
they targeted where they could execute, but two new prompt-side gaps
(undisclosed enums) block the English organisations/tasks paths. No
threshold was changed to evaluate this verdict.

## Remaining risks / next-cycle needs

- Both nondisclosed-enum contract fixes + (optionally) an Orgs/task type
  enumeration note to the packet contracts; version bumps only; then one
  further authorized bounded run targeting fresh evidence destinations —
  the launcher now supports that safely via the override described above.
- Recovery pressure: 5/5 recoveries were consumed; a busier provider day
  could exhaust the recovery limit (fail-closed, no over-budget risk).
- Strict evidence-text equality for non-Latin scripts remains a latent
  extraction failure mode; the failure is honest and fail-closed.
- 4,096-byte capture cap currently truncates large extraction bodies; body
  SHA-256/byte length are retained, so validation evidence is unaffected,
  but full-body semantic review needs the planned uncapped/allowlisted
  capture option (Gate 7 support).

**Next evaluation stage readiness:** pilot_bn is Gate-7-reviewable offline
today; full pipeline Gate-6 re-attempt requires the user-authorized contract
fix cycle described above. H2/full-run/hidden-set work remains NOT AUTHORIZED
and NOT STARTED. The user's instruction to stop after the pilot is honored;
no further code changes were made after the launcher support fix.
