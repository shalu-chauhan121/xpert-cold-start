# Session 12 — Second Live Validation of the Session-11 Contracts (2026-11-10)

**Mode:** user-executed bounded live pilot (explicit authorization action by
running the launcher); agent-side evaluation is offline. **No dev data, no
answer files, no H2/hidden-set work; Gate 6 criteria applied exactly.**

## Run facts

- Model `gemini-3.5-flash-lite`, four synthetic packs only; created
  2026-11-10T14:35:40Z.
- **11 of 25 planned jobs dispatched; 15 transmissions** (≤30), **3
  recoveries** (≤5), **45,922 charged tokens** (≤250,000),
  projected **USD 0.1548** paid-equivalent (Free tier $0), **80.374 s**
  elapsed (≤600 s); `envelope_verified: true`; `synthetic_only: true`;
  `run_state: completed`; stopped: null.
- Tokens: provider-reported **19,005** (10,024 prompt / 8,981 completion);
  conservative reservation 55,036 prompt + 55,296 completion; 3
  unknown-usage attempts fully settled (26,917 reserved, 0 outstanding).
- **Files:** the user's `PILOT_*` variables reused the relative
  `session-10-gate-6-validated-*` names, which resolve to the project ROOT
  (the preserved Session-10 originals live in `ai-logs/opencode/` under the
  same names, untouched). To avoid any collision, the NEW run's artifacts
  were relocated (byte-identical, hash-verified before/after) to
  `ai-logs/opencode/session-12-gate-6-validated-{evidence,captures}.json`
  (SHA-256 `85643B8EA963B2DF…` / `18250D938436B8D4…`; 15 captures).
  Future runs must use genuinely fresh filenames (e.g. `session-13-*`).

## Stage-by-stage

| Stage | pilot_en | pilot_hi | pilot_bn | pilot_hn |
|---|---|---|---|---|
| extraction | 1/2 (window 1 failed provenance) | 1/2 (window 5 failed provenance) | 1/2 (window 0 failed validation) | **2/2** |
| organisations | not dispatched (extraction incomplete) | not dispatched | not dispatched | n/a |
| goals | not dispatched | not dispatched | n/a | n/a |
| entities | not dispatched | not dispatched | not dispatched | n/a |
| tasks | 2 create events succeeded; match phase failed once → 1 pending | not dispatched | not dispatched | succeeded_empty |
| task-match | **dispatched for the FIRST TIME ever** (3rd task job) | – | – | – |
| help | **dispatched for the FIRST TIME ever**; failed validation | n/a | n/a | n/a |

7 of 11 dispatched jobs fully succeeded; 4 failed caller validation, every
one fail-closed, nothing fabricated or repaired.

## Session-11 fix results

- **Issue B (task `details.type`) VALIDATED LIVE:** both successful
  task-create replies used enumerated values (`"type": "followup"`,
  `"type": "commitment"`) with correct message-ID evidence; the
  Session-10 `"task"`/`"request"` substitutions did not recur.
- **Issue A (organisations enums) NOT EXERCISED live:** the English
  organisations stage was never dispatched because its extraction
  prerequisite failed; the offline Session-11 regressions remain the only
  validation.

## Failure diagnosis (each pinned where the capture permits)

1. `extract:cb9459…:1` (en) — `ReasoningError: Evidence text does not match
   original source`, reproduced offline: an org observation cited
   `"HomeServe"` at span 38:47 but body[38:47] is `" through "` (real index
   51). Correct text, wrong offsets → strict provenance rejection, as
   designed.
2. `extract:8aa801…:5` (hi) — reproduction: `दोपहर` transcribed `दपौर`
   (dropped `ह`, changed matra) — the SAME word that failed in Session 10
   (`दपोर`); a recurring model transcription hazard on this exact word.
   Fail-closed.
3. `extract:770f28…:0` (bn) — `ReasoningError` with the body truncated at
   the 4,096-byte capture cap; the failing observation lies beyond the cap
   and cannot be pinned offline. Honest inconclusive detail.
4. `task-review:25f5d5ce…` (en, match phase) — reply
   `{"decision":"none","target":null,"evidence":[]}` rejected: the
   validator requires NON-EMPTY evidence always citing the event's
   source message (tasks.py lines 219-221), which the match packet
   contract does NOT state. **New prompt-side contract gap** (same family
   as Sessions 09/10): the text should require that evidence always
   includes at least the event's source message ID. Validator stays
   fail-closed; fix direction is text + version bump only, in a future
   authorized cycle.
5. `help:cd5a2a87…` (en) — reply used `remind_at:"1789635600Z"`
   (epoch-seconds style) although the prompt ALREADY documents "ISO
   timestamp with explicit offset"; `validate_output` correctly rejected it
   (`invalid timestamp` via `_instant`). **Model compliance failure on
   documented instructions**, not a prompt gap; fail-closed kept. (The
   schema itself accepts any string; the semantic ISO check lives in
   validate_output.)

## Session-08/10 failure-class status re-check

Same as Session 10 where exercised: no name-in-subjects, no unquoted keys
(one acceptable 503 in a transmission row is transport noise, not a parse
outcome — actually 0 `malformed_content` in 15 settled attempts), no
envelope echo, no evidenceless positive records, no hash-as-task-evidence;
503s recurred 3× and were contained (2 recovered to success; 1 recovered
then failed content validation).

## Gate 6 verdict: **NOT PASSED** (documented criteria, applied verbatim)

Envelope/integrity/synthetic-only pass; the pipeline penetrated FURTHER
than ever (task-match + help) but did not finish or honestly complete
end-to-end: three packs' downstream never dispatched because their
extraction prerequisite failed, and the help decision (the last unexecuted
stage family) still has no validated live reply. Both Session-11
enumeration fixes are only partially validated live (task types yes;
organisations enums not exercised). No threshold was changed.

## Ready for the next bounded attempt?

Yes, with preconditions: (1) fresh, unique evidence filenames (`session-13-*`,
ABSOLUTE paths or names under `ai-logs/opencode/` to avoid the root-relative
collision this time); (2) a future text-only cycle for the newly-found
match-phase evidence contract gap (user-authorized, distinct from the live
run); the recurring दोपहर transcription slip and epoch-style remind_at are
model behaviors to observe, not to relax validators for.

**NO claim of Gate 6; H2/full-run/hidden-set NOT started.**
