# Session 11 — Targeted Contract Repair & Offline Verification (2026-11-10)

**Mode:** offline only. **NO LIVE MODEL CALLS MADE.** No pilot launcher run,
no dispatch, no credits consumed, no Gate 6/7/H2 work, no dev/hidden data
access. Pre-edit backup (MD5-verified byte-identical):
`C:\Users\Shalu Chauhan\AppData\Local\Temp\opencode\Xpert-Backup-20261110-195133\`.
No Git initialization.

Scope: the two prompt-side contract ambiguities diagnosed from the Session-10
live captures (`ai-logs/opencode/session-10-gate-6-validated-captures.json`,
SHA-256 823A8EC9350A45D6…; the file's exact location and integrity were
verified before use). Prompt/contract text + version bumps only; no parser,
validator, schema, budget, retry or runtime change; nothing provider-specific.

## Exact enumerations discovered (from the authoritative runtime schema
`schema.json`, cross-checked against `check.py`'s scorer sets)

- Organisations record (required fields id, name, type, side, role):
  - `type`: company, residence, vacation home, workspace, society, school,
    other — exactly one.
  - `side`: home, work (the schema enum has no null; Session-10's nulls were
    also violations).
  - `role`: owner, partner, helper, resident, parent, member, other.
- Task `details.type` (create): commitment, followup, deadline, question —
  matching open_loops `type` in schema.json and `tasks.validate_event`.

## Files changed

- `reasoning.py`: the organisations packet contract now documents all three
  record enumerations verbatim plus "Never substitute an unlisted value or
  null for an enumerated field." `CONTEXT_VERSION` context-4 → **context-5**
  (shared semantic-seam banner, honest provenance for the changed governed
  contract). Task-review `prompt_version` task-review-3 → **task-review-4**.
- `tasks.py`: the task-review packet contract now states `type is exactly one
  of [commitment, followup, deadline, question] - never substitute or invent
  another value`.
- `tests/test_stage_quality.py`: version pins re-pinned to context-5 /
  task-review-4.
- `tests/test_contract_enums.py`: **new, 16 tests** (below).
- Documentation: `WRITEUP.md`, `ai-logs/opencode/INDEX.md`,
  `ai-logs/codex/progress-checkpoint.md`, this file.

## Regression tests added (tests/test_contract_enums.py)

- Documentation coverage: every schema value appears in both contract texts;
  the documented lists equal the schema enums exactly (verbatim
  comma-joined) so the prompts can neither broaden nor omit values;
  "never substitute/invent" guidance asserted.
- Behaviour, organisations (`resolve_organisations` with a scripted client):
  `company` and (second control) `other` with real side/role values succeed
  end-to-end; the captured-style all-null/unlisted record fails closed
  (`incomplete`, `[]`, `organisation_resolution_failed`) and a generic
  invented type (`agency`) fails closed identically; the schema itself is
  asserted un widened (permitted values validate, null and "-unlisted"
  variants rejected by the untouched SchemaValidator).
- Behaviour, tasks (`validate_event`): all four permitted types accepted;
  invented `task`/`request`/`alert` rejected ("Invalid task type"); evidence
  must reference valid message IDs (hash citation rejected, message-ID
  control accepted); unknown owner still fail-closed.
- Neutrality/consistency: no provider/model tokens in CONTEXT_PROMPT or
  either contract; version bumps consistent; old versions absent.

## Offline verification results (exact)

- `python -B -m unittest discover -s tests -v` → **Ran 361 tests in
  12.308 s, OK** (345 + 16 new). Exit 0.
- `python -B -S tests/offline_readiness.py` → both 15,000-message fixtures
  `succeeded`, `exit_status: 0`: sparse 3.884/4.029 s, 599 fake calls;
  dense 39.194/43.838 s, 765 fake calls; identical output
  `output_sha256 5e705c870d5660db…` across both; `python39_grammar`
  checks passed; `imports: passed`; `site_disabled: true`.
- Python-3.9 grammar/import compatibility: via the readiness checks above
  (the documented equivalent command in this project's procedure). No
  separate 3.9 interpreter exists on this machine (recorded finding of the
  earlier H1 review; nothing reinstalled in this session).
- Data-loader smoke: `python -B data.py ..\..\xpert-cold-start\data\dev` →
  `status: succeeded`, 138 chats, 286 people, 4,502 messages, `issues: []`
  (input-only metadata; answers/ never touched).
- Evidence integrity — all five Session-08 artifacts PLUS both Session-10
  artifacts re-hashed unchanged after every edit:
  `3D79BC1E…` stdin-launch, `1079AC05…` partial-run, `0CE77F58…` retry,
  `A062B220…` retry-2 evidence, `A39A885C…` retry-2 captures,
  `42CB1DC7…` Session-10 evidence, `823A8EC9…` Session-10 captures.
- Prompt-version pins and contract-text assertions: covered by
  `test_stage_quality.PromptVersionsTests` (updated) and
  `tests/test_contract_enums.py` (16/16 OK).

## Remaining unresolved risks / next-stage readiness

- Gate 6 remains **NOT PASSED** and is not claimed. The enumerations are now
  documented in the prompts but have NEVER been run against a live model:
  the same caveat as after Session 09 applies.
- The pre-existing "(null if unknown)" phrase in the task contract is
  slightly imprecise (owner may not be null for create; due may be); left
  untouched to avoid scope creep — a candidate for a future text-only
  clarification.
- Recovery pressure (5/5 consumed in Session 10) and strict evidence-text
  equality for non-Latin scripts (the hi transcription slip) remain live-run
  risks; both fail closed as designed.
- 4,096-byte capture cap still truncates large extraction bodies for
  semantic review (byte lengths + SHA-256 retained).
- **Ready for another bounded live-validation attempt:** yes — with fresh
  destination filenames via the launcher's `PILOT_EVIDENCE_PATH` +
  `PILOT_CAPTURES_PATH` override, requiring the user's separate explicit
  authorization. No such run is authorized now.
