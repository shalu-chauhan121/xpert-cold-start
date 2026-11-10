# Session 08 - Stage F task ledger

Stage F implemented at module scope; awaiting user review. No Stage G work.
Read AGENTS.md, revised-plan task boundaries/sections 5-7 and Stage F acceptance
row, latest checkpoint, Stage E observation implementation and synthetic fixture.
The user explicitly authorized Stage F after Stage E review fixes.

## Files and design

- Added tasks.py: evidence validation, candidate retrieval, deterministic ledger
  IDs, accepted-event storage, bounded candidate review and chronological replay.
- Added tests/test_tasks.py: 23 synthetic test methods.
- Added one isolated review_task_packet function to reasoning.py. Explained this
  narrow addition before editing: the approved dependency direction requires
  semantic review through reasoning.py. Existing Stage E functions/tests are
  unchanged. No Stage A-D implementation or existing test was edited.
- Created this report and session-08-transcript.md; appended checkpoint.

build_ledger(data, extraction, reviewer) consumes Stage E observations and a
reviewer(packet, validate). A caller may bind reasoning.review_task_packet to its
run-owned llm.Client. tasks.py creates no client, network connection or files.
Interpretation validates operations, source/spans, known owners, due dates and
required creation fields. An update observation cannot invent a task origin.

Candidate retrieval prioritizes reply/source links, then same-chat candidates,
then other chats with a non-ME shared participant and overlapping object words.
This retrieves candidates only; explicit semantic review must cite both event
and origin to match. Similar titles, shared messages or ME alone never merge
by deterministic rule. Closed-task histories remain available. Candidate IDs are
partitioned (default 16), every partition is reviewed and recorded, and any failed
partition leaves the observation pending. Multiple matches/semantic uncertainty
remain unresolved. Configurable 60000-byte packet limit fails incomplete without
truncating evidence. Large individual packets still need later sizing work.

Origins are established first, then accepted events replay by timestamp, source
line and stable event ID. Creation stays open; acknowledgements do not close;
completion/cancellation set done/dropped with closure evidence; reopening clears
current closure but retains its historical event. Supported reassignment/due
updates preserve status. Replay resets from original details, including after
reassignment. Done/dropped tasks remain in the ledger. No help is generated.

Exact duplicate observations merge window/extraction provenance. Identical
accepted events apply once while retaining each provenance record. Distinct
obligations from one source remain separate. A repeated semantic creation cannot
overwrite the earlier ledger record. Cross-chat closure preserves source/chat.
Predating closures, contradictory creation details, conflicting simultaneous
mutations and uncertain simultaneous origin/closure yield explicit conflicts
and incomplete state rather than arbitrary status. Reviewed ambiguous/unmatched
updates preserve the last supported state with unresolved diagnostics; they are
not silently discarded. Operational failures stay pending/incomplete. Empty
success requires complete extraction and no tasks or unresolved observations.

## Verification

Windows 11 (Windows-11-10.0.26200-SP0), CPython 3.12.9. Project directory:
C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert\xpert-cold-start-starter\cold-start.

| Exact command | Tests | Runtime | Result |
|---|---:|---:|---|
| python -B -m unittest discover -s tests -p test_tasks.py -v | 19 | 0.013s | OK, exit 0 |
| python -B -m unittest discover -s tests -p test_tasks.py -v | 22 | 0.025s | OK |
| python -B -m unittest discover -s tests -v | 217 | 10.348s | OK, exit 0 |
| python -B -m unittest discover -s tests -v | 218 | 10.245s | OK, exit 0 |
| python -B -m unittest discover -s tests -p test_tasks.py -v | 23 | 0.016s | OK, exit 0 |

Final result: 218 passed, zero failures/errors/skips; 23 Stage F tests plus all
195 prior tests. The second full run followed the replay-from-origin correction.
Its preceding focused output was truncated by the combined tool result, so the
focused command was rerun to retain an exact visible timing. No failures observed.
Python 3.9 grammar checks cover tasks.py/reasoning.py; actual 3.9 runtime unverified.

## Limits and stop

Mocked semantic decisions test ledger mechanics, not multilingual interpretation,
negation accuracy, entailment or cross-chat recall. Cross-chat retrieval without
reply links requires shared non-ME participants and object-word overlap; paraphrases
may be missed. Semantic interpretation currently runs per observation and matching
per candidate partition, so call counts/latency/cost need later approved measurement.
No lexical match itself asserts closure. Simultaneous-event handling deliberately
prefers incompleteness over a guessed temporal ordering. Unmatched reviewed events
are quality flags, not proof that no underlying obligation exists.

No live API call, model spend, answer access, checker import/run, installation,
download or full development dataset execution occurred. No Linux or production
readiness claim. No Stage G orchestration, help, export integration or launcher
change. Stop here pending user review and explicit Stage G approval.

## Final verification after simultaneous-closure fix

Verification only; no implementation or test edits in this turn. This entry
supersedes the earlier 218-test final result while preserving its history.
Exact command: `python -B -m unittest discover -s tests -v`
Working directory: C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert\xpert-cold-start-starter\cold-start.
Environment: Windows-11-10.0.26200-SP0; CPython 3.12.9, MSC v.1942,
64-bit AMD64. Actual result: **222 tests in 17.256s; OK; exit 0**.
222 passed, 0 failures, 0 errors, 0 skipped, 0 hanging tests. Synthetic worker
hang scenarios terminated/reaped as expected; the suite itself completed normally.

Confirmed passing in this full run:
- test_simultaneous_completions_have_ambiguous_closure
- test_simultaneous_cancellations_have_ambiguous_closure
- test_simultaneous_conflicting_events_remain_incomplete
- test_simultaneous_closure_replay_is_deterministic
- test_duplicate_closure_event_is_not_distinct_ambiguity

Reviewed the accessible targeted patch and current tasks.py/test_tasks.py source.
Distinct same-time completions/cancellations retain the agreed done/dropped state,
clear closed_by, preserve all events/evidence and record conflicts, so the ledger
is incomplete. Mixed completion/cancellation conflicts retain prior behavior.
Exact duplicate events do not introduce false closure ambiguity.
`git status --short` reported not a Git repository; no repository-wide Git diff
or byte-for-byte baseline certification is claimed. The recorded targeted patch
changed tasks.py and tests/test_tasks.py only; this verification changes docs only.

Reviewed synthetic fixture/fake-client paths and boundary guards. No real answer
files, challenge data or project checker were accessed, imported or executed; no
real API calls occurred. Boundary tests create synthetic answer/checker decoys
and intercept forbidden attempts; those are not challenge answers or the checker.
No downloads/installations. Linux/actual Python 3.9 runtime and production
readiness remain unverified. Stage G not started; wait for explicit user approval.
