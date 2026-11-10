# Progress checkpoint — Stage A completed

## Current status

**Stage A is complete at the data-module level**, including primary assignment and the latest context-validation correction. Context must now be an ordered immediately preceding suffix within its chat and configured overlap limit. The existing loader, splitter, and exactly-once primary checks were not rewritten. Stage B has not started.

The earlier checkpoint correctly identified a gap; this continuation closes it. Assignment coverage is not extraction completion. The implementation report now records the new work above its preserved historical report; the architecture plan is unchanged.

## Completed work and files

- `data.py`: existing loader/indexes/evidence retained; added `MessageSpan`, `ProcessingWindow`, `WindowPlan`, `build_windows()`, and `validate_window_coverage()`. Exactly-once primary coverage, separate preceding context, original IDs, and explicit partial-input status are now available.
- `tests/test_data.py`: 44 synthetic tests: the original 25, 14 window/coverage tests, and 5 latest context-validation tests. These include corrupted assignments, a 30-configuration packing/reconstruction matrix, stale/reversed/excessive context, custom limits, and per-chat overlap history.
- `ai-logs/codex/session-03-implementation.md`: updated with this continuation's decisions, functions, actual test result, and limitations.
- `ai-logs/codex/session-03-transcript.md`: append-only continuation of accessible actual dialogue, including the previous clarification's final response; existing bytes preserved.
- `ai-logs/codex/progress-checkpoint.md`: this updated readiness record.

## Verification

The new test run was on local Windows/Python 3.12. Earlier results below remain historical and were not rerun on development data:

| Check | Actual recorded result |
|---|---|
| **Current:** `python -B -m unittest discover -s tests -v` | **44 tests, 0.475 seconds, `OK`, exit 0.** All previous 39 tests and 5 new tests passed. |
| Before this correction: `python -B -m unittest discover -s tests -p test_data.py -v -k context_overlap_rejects` | 3 regression tests, 0.034 seconds, `FAILED (failures=4)`, exit 1. Reproduced acceptance of invalid context, including two stale/skipped-predecessor subcases. |
| Earlier window implementation: `python -B -m unittest discover -s tests -p test_data.py -v` | 39 tests, 0.539 seconds, `OK`, exit 0. |
| `python -B -m unittest discover -s tests -v -f` | 25 tests, 0.352 seconds, `OK`, exit 0, Windows/Python 3.12. |
| `python -B data.py '..\..\xpert-cold-start\data\dev'` | `succeeded`, 4,502 messages seen/parsed/indexed with valid timestamps; 138 chats; 286 people; no issues or rejected records; exit 0. |
| Original implementation-session preservation check | All 17 snapshotted pre-existing starter-project files unchanged. |

The two preliminary permission failures belong to the original loader session. This correction first reproduced the context bug, then passed the complete synthetic suite after the fix. Durations are actual unittest observations, not benchmarks. No solution execution, model calls, checker runs, answer-file access, or development-dataset window run occurred in this correction.

## Primary coverage: plan requirement versus implemented behaviour

The approved plan explicitly places primary assignment in Stage A. Section 11's Stage A row includes long-message spans and states: “Every primary message/span is covered once”. Section 3 requires exactly one primary assignment per message or long-message span, with overlap excluded from extra coverage. Section 1 assigns window creation to `data.py`; section 2 separates input loading (step 1), window/job creation (step 2), and extraction (step 3). These are plan facts, not a newly proposed redesign.

| Coverage layer | Meaning | Owner and current status |
|---|---|---|
| Loading/indexing | Which nonblank input records were read, parsed, retained, rejected, and uniquely indexed? | Stage A, `data.py`: implemented. A successful load does not prove extraction happened. |
| Primary window/span assignment | Does each message, or every span of a long message, belong to exactly one primary extraction window? Context overlap must not count twice; spans must preserve original message IDs. | Stage A, `data.py`: implemented and tested; validation checks original-body intervals independently of splitting. |
| Processing/extraction | Did each required window/job complete with validated coverage acknowledgement, rather than fail or remain pending? | Stage E extraction, with Stage G orchestration/completion checks in `solution.py`: future work. Acknowledgement alone does not prove that the model found every relevant fact. |

Unsplit messages have one primary window; a long message can span multiple windows, with each nonoverlapping span assigned exactly once under the same original ID. Empty bodies get one [0, 0) span. Undated messages are retained; failed/incomplete input cannot pass `WindowPlan.require_complete()`, even when every indexed message has an assignment. Rejected source lines remain explicit and are not given fabricated evidence IDs.

The validator now enforces context against a bounded ordered per-chat tail, rather than global earlier-primary membership. Nonempty context must be a contiguous immediate suffix in order, with length at most the configured `overlap_spans`; empty context is allowed. This tail may cross earlier window boundaries, matching the unchanged builder. The builder passes its limit to validation, and the coverage report records that limit for later explicit revalidation. Stale, skipped, reversed, excessive, and wrong-chat context fail without changing primary coverage counts.

## Remaining work and next stage

- **Stage A:** no outstanding implementation requirement identified within this scope. The loading, evidence, ordering, and primary assignment gates are covered by synthetic tests.
- **Stage B — next named stage:** broader no-answer boundary tests with synthetic decoys, intercepted opens/no scans, and independence of outputs/request payloads from decoys. Not started; awaits user approval.
- **Stage E / G:** extraction-job completion tracking and final integration of stage/coverage gates. The baseline runner currently does not call the new loader.
- **Platform/readiness work:** Linux and Python 3.9 compatibility remain unverified. The plan places Linux execution/deadline readiness checks in section 9a and Stage H1; Stage A's Windows test result is not Linux certification.
- **Local cleanup:** inaccessible directories from preliminary tests remain a known limitation. The previous report records 25 under `tests/stage-a-*`; first-attempt system-temp leftovers were not enumerated. No cleanup was attempted again in this turn.
- Original parsed dictionaries remain mutable; later consumers must avoid altering evidence records. Unknown dates remain undated rather than guessed.
- Window limits are configurable Python-character/span bounds, not token budgets: defaults are 4,000 primary characters, 32 primary spans, and up to 2 preceding context spans. Metadata/prompt tokens and extraction acknowledgement are later-stage responsibilities. Fixed character splits can cross words or Unicode grapheme boundaries; original text is retained exactly and can be reconstructed.
- The coverage dictionary is a snapshot. Revalidate against the original input if a future consumer changes assignments; do not mutate preserved input or coverage reports. The standalone CLI still reports loading only.

Stop here pending approval. No Stage B or change to the six-module architecture was performed.


## Session 04 update - Stage B ready for review

This appended entry supersedes the earlier "Stage B not started" status above;
all preceding checkpoint history is preserved. Stage A remains approved and
unchanged. Stage B now has six deterministic tests in
`tests/test_no_answer_boundary.py`, including 19 negative-control subcases.

Synthetic inputs and decoys are isolated in test-owned directories. Guards cover
module initialization and execution, intercept file opens, reject directory scans
and checker imports/execution, and retain violations even when exceptions are
caught. Only the three input files are readable; output and usage paths are
write-only. No real answers or real model/API calls were used.

The baseline still lacks model orchestration. Stage B therefore compares actual
baseline output bytes separately from a test-only loader/window-to-client probe
with one nonempty wire request and a fixed reply. Identical inputs with/without
decoys produce identical requests, replies, baseline outputs, and usage logs.
A changed permitted participant changes requests and baseline output. Future
integration must apply these boundary checks to its actual orchestration; this
entry does not claim completion of later stages.

Verified on Windows/Python 3.12.9, from `xpert-cold-start-starter/cold-start`:

| Exact command | Actual result |
|---|---|
| `python -B -m unittest discover -s tests -p test_no_answer_boundary.py -v` | 6 tests, 7.998s, OK, exit 0 |
| `python -B -m unittest discover -s tests -p test_data.py -v` | 44 tests, 0.677s, OK, exit 0 |
| `python -B -m unittest discover -s tests -v` | 50 tests, 8.390s, OK, exit 0 |

Three initial Stage B harness runs failed (9, 17, then 1 unittest failures).
Windows access-mask handling, codec preloading, and per-run artifact reset were
corrected; all final runs pass. Exact failed-run durations and commands are in
`session-04-implementation.md` and `session-04-transcript.md`. No Stage B fixture
directories remained after cleanup. Old Stage A cleanup limitations remain
historical and were not revisited.

Files added: the Stage B test file and the two Session 04 logs. This checkpoint
is appended; prior session logs, Stage A code/tests, and runtime files are
unchanged. No dependencies were added. Linux/Python 3.9, model accuracy, final
schema validation, and future model integration remain outside this verification.

**Stage B is ready for user review. Stop here. Stage C has not started and
requires explicit user approval.**


## User approval - Stage B closed at its documented scope

The user has approved Stage B at its documented input-isolation scope. This
supersedes the pending-review status above. Preserve the existing implementation,
tests, Session 04 report and transcript, and all prior checkpoint content. No
further Stage B code changes are authorized by this approval.

Carry forward this explicit Stage G acceptance requirement: test the actual
production entry point with identical permitted inputs, fixed mocked responses,
and absent/present synthetic decoys; verify identical requests and final outputs
under the same boundary guards, and verify that supported changes to mocked
responses affect output. Stage B approval does not establish this future
integration evidence.

Stage C has not started. Wait for the user's Stage C implementation prompt.


## Session 05 update - Stage C completed; awaiting review

The user authorized Stage C implementation after approving A/B. This appended
entry supersedes the prior "Stage C has not started" status and preserves all
preceding checkpoint bytes. Stage D has not started and still requires explicit
user approval.

Added `validation.py` with the actual local schema, the plan's exact supported
vocabulary, explicit unsupported-keyword/configuration failures, JSON-pointer
errors, reference/coverage checks, closure chronology, help requirements and
calendar/reminder validation. Selected one backend: **xpert-scoped-schema 1.0.0**,
standard-library only, targeting the existing Python 3.9+ Linux contract.
Installed Windows jsonschema 4.26.0 requires Python >=3.10; no cached wheels or
usable Linux environment were available. A fresh process with site packages
and network access disabled passes. A development-only Draft 2020-12 reference
agreed on 141 schema checks; it is not a production dependency or fallback.
Actual Linux/Python 3.9 execution remains unverified, not an H1 pass.

`solution.py` retains two CLI arguments, uses Stage A loading, rejects incomplete
input/inference, and publishes only after validation, exclusive destination-side
temporary creation, serialization, flush/fsync/close, strict rereading, validation
and atomic replacement. Handled failures preserve old bytes and clean owned
temporaries. Uncatchable kills can leave an unpublished temporary.

Nonempty production inference intentionally returns nonzero at Stage C: the old
blanket classifications and unexplained empty goals/loops cannot count as completed
inference. Only truly empty input completes without later stages. Synthetic tests
patch the assembly seam while exercising real loading, validation and export.
Stage B's guard was narrowly adapted to the local schema and owned temporary
artifact, and its naive producer moved into the test harness. Its no-answer/no-scan/
no-evaluator/no-network guarantees and existing negative controls still pass.
`data.py` and `tests/test_data.py` were not changed. The Stage G production-model
orchestration acceptance requirement recorded above still applies.

Final verification on Windows/Python 3.12.9, from the starter's `cold-start` directory:

| Exact command | Actual result |
|---|---|
| `python -B -m unittest discover -s tests -p test_validation.py -v` | 61 tests, 1.436s, OK, exit 0 |
| `python -B -m unittest discover -s tests -p test_data.py -v` | 44 tests, 0.439s, OK, exit 0 |
| `python -B -m unittest discover -s tests -p test_no_answer_boundary.py -v` | 6 tests, 7.308s, OK, exit 0 |
| `python -B -m unittest discover -s tests -v` | **111 tests, 10.425s, OK, exit 0** |

The initial 57-test Stage C run and 13-test/141-comparison reference run also
passed; exact commands, durations, backend evidence and operational failures are
in `session-05-implementation.md` and `session-05-transcript.md`. No tests failed.
No Stage B/C fixture directories remain. Earlier Stage A cleanup history is
unchanged. No prior logs, schema, launcher or model client were edited.

Created: `validation.py`, `tests/test_validation.py`, and both Session 05 logs.
Modified: `solution.py`, `tests/test_no_answer_boundary.py`, and this appended
checkpoint. Reference validity is not textual entailment; reviewed semantic links,
extraction completeness and real inference remain later-stage responsibilities.
No actual answer files were accessed, evaluator imported/invoked, real model/API
calls made, dependencies downloaded, or full-dataset/readiness runs performed.

**Stage C is complete at its implementation scope and ready for user review.
Stop here. Stage D has not started.**

## Session 06 milestone 1 - Stage D design and context read

Read AGENTS.md, architecture, revised plan (including sections 1, 8, 9,
9a, 10, 11, 11a), checkpoint, llm.py, solution.py, existing test contracts,
and Stage C report. Stage D only is authorized. No source changes yet.
The workspace root is a container; project is xpert-cold-start-starter/cold-start
and is not a Git checkout. Initial root AGENTS.md read failed; located the project.
Installed tokenizers 0.23.1 imports, but no model-specific tokenizer is configured;
tiktoken/transformers are absent. Use a labelled UTF-8 proxy with calibration.
No package installation, network/model call, dataset or answer access occurred.

Next: implement llm.py with structured exceptions, injectable transport/clock,
spawned HTTP worker with bounded termination, shared reservations/recovery ledger,
and run-local validated cache. Then synthetic tests and narrowly adapt Stage B's
transport mock. No Stage E, launcher edits or Linux readiness claim.

## Session 06 milestone 2 - Client implementation saved

Replaced llm.py with the Stage D client, Budget, Deadline and ProcessTransport.
Public chat signature is preserved; failures are structured exceptions. Added
shared 20% recovery/three-transmission accounting, atomic reservations, unknown
usage retention, calibrated UTF-8 proxy, explicit output cap, and in-memory cache.
Spawned workers use bounded shared memory and terminate/kill/reap cleanup.
No production integration or Stage E changes. No usage.jsonl raw/disk logging.

Verification: python -B -c "import ast, pathlib, llm; ast.parse(pathlib.Path('llm.py').read_text(), feature_version=(3, 9)); print('llm import and Python 3.9 grammar: OK')"
Result: exit 0, import and grammar pass. Mandatory tests not yet implemented/run.
Next: add tests/test_llm.py, adapt Stage B fake transport and in-memory usage
comparison without relaxing its data/network guards, then run focused suites.
Stage D is NOT yet complete.

## Session 06 milestone 3 - Resume review and independent baseline verification

User explicitly requested continuation, preserving the saved implementation.
Re-read current guidance/checkpoint/client and inspected test contracts; the
architecture/plan and Stage A-C context were already read in this accessible
conversation. No Session 06 implementation/transcript files existed yet.
Saved files present: llm.py, tests/test_llm.py, narrow Stage B mock adaptation.
Independent Windows/Python 3.12.9 reruns (exit 0, no failures):
- python -B -m unittest discover -s tests -p test_llm.py -v: 49 tests, 3.002s, OK.
- python -B -m unittest discover -s tests -p test_no_answer_boundary.py -v:
  6 tests, 10.729s, OK.
Earlier accessible runs were 49 tests/2.721s and 6 tests/7.334s, also OK.

Review found missing regression coverage for dispatch preparation consuming time,
non-numeric Retry-After causing early retries, and partial detail usage exceeding
reservations. Next: add regressions, fix only these acceptance gaps and related
accounting/cleanup checks, run focused then mandatory full suite, save both
Session 06 records. Stage D remains incomplete until final verification/docs.

## Session 06 milestone 4 - Review fixes verified

Changed only llm.py and tests/test_llm.py during this resume. Added seven
regression tests; first run reproduced all seven issues (10 failures including
Retry-After subcases):
- python -B -m unittest discover -s tests -p test_llm.py -v -k regression:
  7 tests, 0.032s, FAILED (failures=10), exit 1.
After fixes:
- python -B -m unittest discover -s tests -p test_llm.py -v:
  56 tests, 2.578s, OK, exit 0.

Fixed dispatch checks after preparation, absolute worker deadlines covering setup,
expired-worker refusal, permanent certificate failure classification, unsupported
Retry-After rejection without early retry, positive reservations/current safety
factor recheck under lock, and known usage-detail lower bounds. Added explicit
retry/category totals and retained bounded cleanup with exit-race handling.
Existing real spawn/hang/partial-transfer/crash/reap tests all pass on Windows.

Next: run the required complete suite, create the concise Session 06 report and
abbreviated factual transcript, append final checkpoint. No Stage E or Linux
readiness claim. No real API/dataset/answer access occurred.

## Session 06 final update - Stage D complete at implementation scope; awaiting review

This appended status supersedes the incomplete Stage D milestone entries above;
all earlier checkpoint content is preserved. Stage E has not started.

Completed llm.py client/Budget/Deadline/ProcessTransport implementation with the
unchanged public chat signature, structured safe failures, environment-only
configured chat endpoint, bounded shared recovery and original-job limits,
atomic token reservations, conservative unknown usage, calibrated byte estimates,
validated run-local cache and bounded spawn-worker cleanup. Seven reproduced
review gaps were corrected without redesigning the saved implementation.

Files changed in Session 06:
- llm.py (implementation and necessary review fixes).
- tests/test_llm.py (56 synthetic tests).
- tests/test_no_answer_boundary.py (earlier narrow transport/in-memory-ledger
  adaptation; existing boundary protections retained, usage writes disallowed).
- ai-logs/codex/session-06-implementation.md (created).
- ai-logs/codex/session-06-transcript.md (created; explicitly abbreviated).
- ai-logs/codex/progress-checkpoint.md (appended milestones and this status).
No protected runtime files, Stage A/C tests, approved plans or prior session
reports/transcripts were changed. No Stage E module or launcher change.

Final mandatory verification, Windows 11/CPython 3.12.9, project cold-start cwd:
`python -B -m unittest discover -s tests -v`
**167 tests in 9.999s; 167 passed, 0 failures, 0 errors, 0 skips; OK; exit 0.**
Includes 44 A + 6 B + 61 C + 56 D tests. Focused post-fix run:
`python -B -m unittest discover -s tests -p test_llm.py -v`
56 tests in 2.578s; OK; exit 0. Earlier baseline and intentional regression
failures are preserved above and in both Session 06 records.

No remaining implementation/test requirement identified within Stage D's client
scope. Outstanding later-stage limitations: integrate a run-start/shared budget
and finalization gate in the future orchestrator; supply stage-specific schemas,
validators and cache context; verify actual provider/tokenizer/prices/quotas.
An estimate cannot guarantee a true billing ceiling for an unknown tokenizer.
Default token ceiling is unset; recovery is disabled without declared base calls.
Non-numeric/HTTP-date Retry-After stops recovery safely. No splitting implemented.

Real spawned-worker termination/reaping passed on Windows. Actual Linux signals,
process groups, launcher hard timeout, hung-parent cleanup and Python 3.9 runtime
remain unverified; grammar checks are not execution evidence. The client reserves
27:00/29:30/30:00 time boundaries but cannot guarantee whole-process exit without
future orchestration and the approved Linux launcher work. No production/Linux
readiness claim. No real model/API call, paid experiment, answer-key access,
evaluator import/execution, installation/download or full-dataset run occurred.

Exact next step: user reviews the Session 06 report and changes. Wait for explicit
approval before any Stage E work. Stage D is complete at this documented scope.

## Session 07 milestone - Stage D approved; Stage E partial

User approved Stage D and authorized Stage E only. Added reasoning.py extraction
and tests/test_reasoning.py (8 tests). Exact primary coverage, citation spans,
original text and overlap provenance checked; failures remain incomplete.
All prior runtime files/tests preserved. Created Session 07 implementation report
and explicitly abbreviated transcript. Stage E is NOT complete.

Tests: python -B -m unittest discover -s tests -p test_reasoning.py -v
8 tests, 0.006s, OK. Full: python -B -m unittest discover -s tests -v
175 tests, 12.176s, OK, 0 failures/errors, exit 0 (Windows/Python 3.12.9).

Remaining: canonical organisation/alias resolution; people/circle/link/chat
resolution and seed preservation; entity completeness; supported goal dispositions,
semantic merging and exact section 4a ranking/top ten; their acceptance tests.
Exact next step: read section 4a in full and add organisation-resolution contract
and shared-participant/alias tests in existing reasoning.py/test_reasoning.py.
Continue authorized Stage E without rebuilding extraction. Stage F is forbidden
until Stage E completion and explicit approval. No real API/spend, answer access,
installs, evaluator execution or full-dataset run occurred. No readiness claim.

## Session 07 continuation - Stage E resolvers implemented; review pending

Preserved extraction and its eight tests. Added organisation/alias resolution,
global people/circle/link/chat decisions with seed protection, exact entity batch
coverage, semantic goal dispositions/merging and deterministic evidence-tier
ranking/top ten in reasoning.py. Added tests/test_reasoning_resolution.py (15
new tests). Completed Stage A-D files/tests were not edited. Appended both
Session 07 records, preserving earlier partial-work chronology.

Focused command: python -B -m unittest discover -s tests -p 'test_reasoning*.py' -v
23 tests, 0.051s, OK. Earlier continuation run: 19 tests, 0.040s, OK.
Required full command: python -B -m unittest discover -s tests -v
190 tests, 12.476s, OK, 0 failures/errors, exit 0, Windows/Python 3.12.9.

Remaining limitations: mocked semantics do not prove inference accuracy; packets
above configured byte bound remain incomplete; scalable partition recovery and
live feasibility remain unverified. UTC is a configurable default, not a dataset
fact. Linux/Python 3.9 execution and production readiness are not established.
No real API calls/spending, answers, evaluator, installs or full-dataset execution.
No Stage F/G work. Exact next step: user reviews Stage E implementation and test
coverage; wait for approval before Stage F. See Session 07 report for details.

## Session 08 - Stage F implemented; awaiting review

User explicitly authorized Stage F. Added tasks.py and tests/test_tasks.py;
added only review_task_packet to reasoning.py for the plan-required semantic
review boundary, explained before editing. Existing Stage A-E tests preserved.
Created session-08-implementation.md and abbreviated session-08-transcript.md.

Implemented evidence validation, deterministic identity/provenance, candidate
retrieval/partition review, accepted-event ledger and chronological replay.
Covers creation/acknowledgement/update/completion/cancellation/reopening,
reassignment, duplicates, same-source distinct tasks, cross-chat closure,
reviewed ambiguity and incomplete processing. Conflicting/predating/simultaneous
uncertain changes remain explicit; no guessed status. Replays restart at origin.
No help decisions or final orchestration added.

Final focused: python -B -m unittest discover -s tests -p test_tasks.py -v
23 tests, 0.016s, OK, exit 0.
Final full: python -B -m unittest discover -s tests -v
218 tests, 10.245s, OK, 0 failures/errors/skips, exit 0.
Windows 11/CPython 3.12.9; actual Linux/Python 3.9 runtime unverified. Grammar
checks pass. Earlier 19/22-test and 217-test results retained in Session 08 report.

Remaining limitations: semantic/cross-chat recall unverified, per-observation
review cost unmeasured, oversized individual packets fail incomplete, reviewed
unmatched events remain quality flags. No API/spend, answer/checker access,
installs or full-dataset run. No production/Linux readiness claim.
Exact next step: user reviews Stage F. Wait for explicit approval before Stage G.

## Stage F final verification after targeted closure fix

User requested verification only. Ran documented command:
`python -B -m unittest discover -s tests -v`
Windows 11/CPython 3.12.9 (64-bit AMD64): **222 passed, 0 failures/errors/skips,
0 hangs; 17.256s; OK; exit 0**. Same-time completion/cancellation, mixed conflict,
deterministic replay and duplicate-closure regression tests all passed.

Reviewed current targeted code/tests against the accessible patch record.
No Git checkout is available, so no repository-wide Git diff certification.
No implementation/test changes were needed. Appended Session 08 report,
transcript and this checkpoint; previous history preserved.
No real answers, challenge data, project checker or real API calls accessed.
Synthetic boundary decoys remain intercepted test fixtures. No Stage G work.
Exact next step: user reviews final Stage F verification and explicitly approves
any Stage G work. Linux/Python 3.9 runtime and production readiness unverified.

## Session 09 - Stage G integrated; awaiting review

User authorized Stage G only. Production solution.py now runs existing data,
extraction, organisation/entity/chat/goal resolution and task ledger stages,
requires complete stage states, obtains help for open loops, assembles exactly
five arrays and uses unchanged Stage C rules with deadline-gated atomic export.
Shared client/budget starts with run timing; diagnostics/provenance remain internal.
Added resolve_help in reasoning.py and timeout wrapper in run.sh (1770s TERM,
2s kill grace, missing timeout utility fails). No Stage H/benchmarking performed.

Changed: solution.py, reasoning.py, run.sh, new tests/test_solution.py; two narrow
existing harness adaptations in test_validation.py and test_no_answer_boundary.py.
Created Session 09 report/abbreviated transcript; prior history preserved.
No data.py/llm.py/tasks.py/validation.py/schema or approved plan edits.

Final focused: python -B -m unittest discover -s tests -p test_solution.py -v
9 tests, 0.287s, OK, exit 0.
Final full: python -B -m unittest discover -s tests -v
231 tests, 13.107s, OK, 0 failures/errors/skips/hangs, exit 0.
Windows 11/CPython 3.12.9. Earlier runs recorded in Session 09 report.
Production-entry tests use fake HTTP and input-read/scan/network guards; decoys
leave requests/output unchanged and changed mocked help changes output.

Limitations: Linux hard-timeout/process-group execution NOT verified; direct
Python invocation has no outer supervisor. Actual Python 3.9, live accuracy,
provider/cost/volume feasibility and complete cold-run deadlines remain unverified.
No readiness or benchmarking claim. No real API/spend, answer/checker/challenge
input access, installation or download. Exact next step: user reviews Stage G
changes and limitations; wait for explicit approval before further work.

## Session 10 — H1 offline review, 2026-11-05

Completed available Windows offline checks; H1 readiness gates remain unmet.
No production implementation or existing test changes. Added explicit synthetic
probe tests/offline_readiness.py, Session 10 report/abbreviated transcript;
appended this checkpoint. Historical records preserved.

Environment: Windows 11 build 26200, CPython 3.12.9 AMD64. WSL not installed,
Docker/Python 3.9 not discovered. Git Bash cannot create signal pipe (error 5;
exit -1073741502), so launcher syntax/execution and Linux supervision unverified.
All six production modules pass 3.9 grammar parsing and offline imports under -S;
this is not actual 3.9 runtime verification. No Git repository/diff available.

Exact final commands/results:
- python -B -m unittest discover -s tests -v: 231 passed, 14.075s, exit 0.
- python -B -m unittest discover -s tests -p test_llm.py -v: 56 passed, 2.646s, exit 0.
- python -B -m unittest discover -s tests -p test_solution.py -v: 9 passed, 0.353s, exit 0.
All suites: zero failures/errors/skips/hangs; Windows spawned-worker cleanup and
atomic output/failure safety pass.
- python -B -S tests/offline_readiness.py: final exit 0; six module imports/grammar
and two 15,000-message fixture assertions pass. Sparse pipeline 6.589s, peak traced
Python allocations 34,595,896 bytes, 599 fake calls, success. Dense 15.055s,
74,426,040 bytes, 594 fake calls, incomplete entities; existing output preserved.
Dense entity context measured 11,119,951 bytes versus 100,000-byte configured cap.
This demonstrates a scaling limitation; no 30-minute guarantee, RSS estimate,
real inference accuracy or production readiness claim. Report records earlier
harness failures and successful intermediate runs honestly.

No challenge inputs/answers/checker, API/spend, package installation or download.
Remaining: actual Linux launcher/group/signal/outer-timeout tests, actual Python
3.9 runtime, clean offline Linux packaging, context scaling and realistic latency/
cost evidence. Exact next step: user reviews H1 evidence/limitations and approves
any subsequent work. Live pilot/full challenge execution remain unauthorized.

## 2026-11-05 - Session 10 dense-context diagnosis only

Root cause confirmed: resolve_entities batches only required IDs (32/29 here),
repeating all observations, cited full messages, schema/chats/seed per batch.
Read-only in-memory inspection of the existing dense synthetic probe measured
11,119,951/11,119,900-byte packets; 15,006 unique observations, 15,000 messages.
First packet: observations 6,888,357 bytes, full messages 4,222,040 bytes;
window-ID arrays within observations 1,197,854 bytes. Exact overlap duplicates
are already merged; independently sourced identical text must not be collapsed.
Cap failure occurs before entity dispatch and correctly preserves prior output.

Actual command: PowerShell here-string piped to python -B -S - (complete body
in Session 10 transcript), temporarily wrapping _call in memory and invoking
probe.volume(dense=True). Exit 0; expected incomplete entity result, 594 fake
calls, preserved output; 21.830s, 74,508,701 traced bytes WITH diagnostic overhead.
No full-suite rerun for this documentation-only change. Historical 231-pass
results remain historical; no proposed-fix tests have run.

Recommendation pending approval: compact original evidence with full local
provenance; preplanned byte-bounded partitions plus target/evidence coverage;
validated partial proposals; deterministic agreeing-field/evidence merging;
bounded conflict review or pending state. Preserve IDs, seed circles, explicit
dated/undated ordering, original-job recovery caps and final output validation.
No increased packet limit, silent truncation or last-response-wins merge.
Transient packet buffers shrink; total cache/provenance memory and model-call
latency may grow. No numeric runtime/30-minute guarantee. Other stage caps remain.

Required after approval: dense and sparse 15,000-message regressions, packet bounds,
evidence/window provenance, deterministic reruns/order, cross-chat consistency,
conflict/partial/oversized/budget/timeout safety, atomic preservation; then focused
tests, volume probe and full suite with measured results. Detailed scope and risks
are appended to Session 10 report. H1 NOT passed; issue NOT fixed.

Changed only Session 10 report/transcript and this appended checkpoint; all prior
history retained. Production code and existing tests unchanged. No forbidden
data/checker/network/API/install operations. Exact next step: wait for explicit
approval, then add failing regressions and implement the bounded entity proposal,
update necessary synthetic mocks and run the specified verification. Do not start
implementation, live inference or full challenge execution before approval.

## 2026-11-05 - Approved bounded entity fix verified offline

User approved the prior proposal. Completed only entity partitioning/merging in
reasoning.py; added tests/test_entity_partitions.py and updated the explicit
tests/offline_readiness.py probe. Appended Session 10 report/transcript and this
checkpoint; historical entries retained. No other runtime module/existing unit
test edited. No H2/live inference authorization.

Before production edits: 7 new regressions ran, 2 passed/4 failures/1 error in
0.023s, exit 1. Implemented entity-3 compact evidence packets, full local original
observation/window registry, chronological stable ordering, preplanned complete
target/evidence coverage, scoped citations and deterministic compatible merging.
All evidence is conservatively reviewed by every target batch. Conflicts, nulls,
missing work, oversized units/fixed context remain incomplete. No last-wins or
automatic conflict-review call. Original seed/client/budget/retry/deadline/final
validation/atomic publication safeguards retained.

Final exact commands:
- python -B -m unittest discover -s tests -p test_entity_partitions.py -v:
  13 passed, 1.214s, exit 0.
- python -B -m unittest discover -s tests -p 'test_reasoning*.py' -v:
  28 passed, 0.073s, exit 0.
- python -B -m unittest discover -s tests -p test_solution.py -v:
  9 passed, 0.354s, exit 0.
- python -B -m unittest discover -s tests -v:
  244 passed, 13.229s, exit 0; zero failures/errors/skips/hangs.
- python -B -S tests/offline_readiness.py: final exit 0; both 15,000-message
  fixtures complete with identical validated output hashes and full per-target
  evidence coverage. Sparse 7.053s / 34,595,800 traced bytes / 599 calls / 2 entity
  packets (max 11,770 bytes). Dense 55.022s / 71,399,529 traced bytes / 765 calls /
  168 entity packets (max 99,961 bytes). Six production imports and Python 3.9
  grammar checks pass. Earlier passing runs and initial red tests are in report.

Windows 11 build 26200 / CPython 3.12.9 AMD64. Memory is traced Python allocation,
not RSS. Timing excludes input creation, uses fake model latency/deadline clocks;
full suite overlapped part of final dense run. Context JSON is <=100,000 bytes;
outer HTTP JSON request measured up to 112,560 bytes after escaping/settings,
which Stage D includes in reservations. No total HTTP-size guarantee implied.

Dense-context failure addressed for these fixtures, but overall H1 NOT passed.
Conservative broadcast costs extra calls; total cache/provenance memory scales.
Other stage caps, indivisible/fixed overflow and unresolved semantic conflicts
remain limitations. No real inference accuracy/30-minute or production readiness
claim. Linux and actual Python 3.9 runtime remain unverified. No prohibited data,
checker, real network/API, install/download or challenge execution occurred.
Exact next step: user reviews this fix and measured limitations. Stop; do not
start H2/live work or further implementation without explicit approval.


## 2026-11-05 - Approved recovery of Sessions 06-10 transcripts

User approved export after read-only source investigation. Recovered the original
recorded dialogue and tool activity into session-06-transcript.md through
session-10-transcript.md. Each file retains its previous abbreviated transcript
byte-for-byte as a clearly labelled historical appendix. No historical content
was deleted or used to fabricate missing dialogue.

Source: C:\Users\Shalu Chauhan\.codex\sessions\2026\11\04\
rollout-2026-11-04T22-47-24-01a1a790-c437-7d52-aab8-8223fb3e6c41.jsonl.
Source ranges: Session 06 lines 12-221; 07 lines 222-368; 08 lines 369-511;
09 lines 512-586; 10 lines 587-889. Each export records its source-range SHA-256,
original UTC timestamps/line numbers and the historical appendix SHA-256.

Recovered 12 task prompts plus one environment-context message, 46 assistant
messages, 99 tool calls with 99 matching outputs, 91 command-execution events
and 38 file-change events. Duplicate UI dialogue, internal reasoning/configuration
and compaction replacement summaries were excluded. Model-facing truncation is
preserved honestly; longer raw command output is separately labelled rather than
presented as text the model necessarily saw. Session 06's first turn has no
recorded final assistant answer; the export explicitly states this gap.

Verification: all selected text blocks matched source content, all tool-call IDs
paired with outputs, all historical appendix bytes/hashes preserved, and source
prefix through line 889 unchanged before/after export. Destination writes were
verified and atomically replaced. Follow-up checks revalidated appendix and
source-range hashes. Documentation-only change; no project test suite rerun.

Changed only the five transcript files and this appended checkpoint. No production
code/tests, original Codex records, challenge inputs/answers or checker were
modified/accessed. No API/network/download/install activity. Current Codex may
append this recovery conversation to its active rollout automatically; the
historical source ranges themselves were not edited. Recovery is complete relative
to recorded content, not a claim about output never captured. H1/runtime limitations
remain unchanged. Stop for user review; no H2/live inference authorized.

## 2026-11-05 — Session 11 remaining H1 verification

Continued offline verification without production/test changes. Windows 11 /
CPython 3.12.9: `python -B -S tests/offline_readiness.py` passed six imports,
Python 3.9 grammar and both 15,000-message mocked pipelines (exit 0). Sparse:
4.244s, 34,595,776 traced bytes, 599 fake calls. Dense: 30.725s, 71,398,973
traced bytes, 765 fake calls, 168 entity packets, largest context 99,961 bytes.
Both validated outputs retain the previously recorded identical hash.
`python -B -m unittest discover -s tests -v`: 244 passed, 11.371s, exit 0.

WSL is not installed; no Docker command found. Registered/inspected Python
runtimes are 3.12 only. Git Bash syntax probe failed at startup with signal-pipe
Win32 error 5. Linux execution/process-group behavior and Python 3.9 runtime
remain unverified. Static launcher review found LF endings and existing timeout
limits intact; production imports remain standard-library/local only.

Deviation: `PYLAUNCHER_ALLOW_INSTALL='0'; py -3.9 --version` unexpectedly
announced launching winget to install Python. No retry; subsequent process check
found no winget/AppInstaller and inspected installation directory still only
Python312. No installation/download success was reported, but absence of a
launcher network attempt cannot be certified. See Session 11 report/transcript.
No real model API, challenge input/answer access or checker execution occurred.

Actual conversation is exported into new session-11-transcript.md from its
original local record, with ongoing updates and final-response capture support.
Earlier transcripts remain intact. Detailed results: session-11-implementation.md.
H1 remains incomplete; stop for review. H2 has not started and requires approval.


## 2026-11-05 ? Session 12 Ubuntu / Python 3.9.25 validation

User-reported Ubuntu CPython 3.9.25 validation:

- All 244 unit tests passed in 64.844 seconds.
- All 6 no-answer-boundary tests passed.
- Linux offline readiness and both synthetic fixtures passed.
- All six production SHA-256 hashes match their original recorded values.

These Linux results were supplied by the user, not rerun from this Windows
session. They resolve the previously recorded Linux/Python 3.9 validation gap
for the checks reported above; no additional launcher or timeout measurements
are inferred. Mocked success does not establish real-model quality or latency.

The only implementation change in this investigation was the test-only
audit-event accounting correction in `tests/test_no_answer_boundary.py`:
read and write entries retain the audit mode, and logical read/write counts
include only high-level events (`mode is not None`). Both audit events remain
recorded; every event still undergoes the existing path, flags and permission
checks. Forbidden-file, directory-scan, checker import, network, request and
output checks remain intact. No production implementation changed.

Local Windows CPython 3.12.9 validation after the write correction:
`python -B -m unittest discover -s tests -p test_no_answer_boundary.py -v`:
6 tests passed in 6.565 seconds. The earlier read-only correction passed the
same 6 tests in 7.101 seconds locally but required the subsequent write fix
on Ubuntu. Session 12 implementation and actual transcript records are in
`session-12-implementation.md` and `session-12-transcript.md`.

This records update did not access challenge data or answer/checker files,
run check.py, call real model APIs, install runtimes or access WSL. H2/live
inference has not started and is not authorized by this records update.


## 2026-11-05 - Session 13 consolidated no-spend H1 work

Consolidated evidence, all nine Section 11a statuses, the input-only forecast
method and bounded synthetic live-pilot proposal are in
`session-13-h1-readiness.md`. H1 is NOT complete: gates 1, 2, 3 and 5 PASS;
gates 4, 6, 7, 8 and 9 remain BLOCKED. No live pilot or H2 was authorized/run.

Established Ubuntu 26.04 / WSL 2 Python 3.9.25 results (244 unit tests, six
boundary tests, both 15,000-message fixtures and unchanged production hashes)
were reused. Agent WSL launch failed with WSL/Service/E_ACCESSDENIED; this is
an execution-channel limitation, not a claim that Ubuntu is absent.

Added only the missing display-name renaming regression and standalone
`tests/linux_acceptance.py`. Targeted solution tests: 10 passed in 0.436s.
One full Windows Python 3.12.9 suite: 245 passed in 12.829s, exit 0, saved in
`session-13-unit-tests.txt`. New Linux harness parses as Python 3.9 but has not
run on Linux; `session-13-linux-acceptance.json` records BLOCKED preflight.
All six production hashes still match. No production files changed.

The original actual conversation is exported to `session-13-transcript.md`
using `session-13-export.py`; earlier transcripts/reports remain preserved.
No challenge inputs/real answer or checker files, model API calls, spending,
installations or downloads were used in this task. Existing synthetic tests
continue to use their own decoys only.

Exact next action on the installed Ubuntu environment, from the project:
`python3.9 -B -S tests/linux_acceptance.py --report ai-logs/codex/session-13-linux-acceptance-ubuntu.json`.
Inspect every scenario result and cleanup evidence before accepting gate 4.
The command has not run here. A live pilot requires separate explicit approval
and model/endpoint/pricing/spend controls. Input metadata and pilot measurements
are still required for the full-run forecast; full-run approval is separate.


## 2026-11-06 - OpenCode Session 01 - launcher_hang acceptance fix verified

Diagnosed the single Section 9a failure in session-13's Ubuntu run: the
installed uutils timeout 0.8.0 skips its kill-after group SIGKILL
(`ChildExt::send_signal_group` aborts because `signal(SIGKILL, SIG_IGN)`
returns EINVAL), so the TERM-ignoring orphan survived holding the harness
stdout/stderr pipes and `communicate(timeout=20)` masked the real 137 result.
GNU timeout kills the whole group including itself (documented "137 if
COMMAND (or timeout itself) is sent the KILL signal"), which the test encoded.

Changed only `run.sh`: blind `exec` replaced with wait + killpg backstop
(`timeout ... & leader=$!; wait; status=$?; kill -KILL -- "-$leader"; exit
"$status"`). Deadline 1770s, 2s kill grace, usage/missing-timeout exits and
0/1/124/137 exit codes preserved; `--kill-after=2s 1770s` still occurs exactly
once, so harness content assertions and the copied-launcher rewrite hold.
No production Python files, harness, or test files changed.

Focused verification on WSL2 Ubuntu 26.04.1 / uv CPython 3.9.25 by importing
the unmodified `tests/linux_acceptance.py` and calling `run_case()` directly
(temp verifiers outside the repo); only the specified scenarios ran:
- launcher_hang: PASS, exit 137, 13.148s, no leftover processes,
  markers main_started+orphan_started.
- launcher_success: PASS, exit 0, 0.705s, no leftovers, no markers.
- interrupted_write: PASS, exit 124, 12.265s, no leftovers, both markers.

The other seven scenarios and the full suite were not rerun (history stands).
GNU-timeout equivalence is source-reasoned, not executed. Details:
`ai-logs/opencode/session-01-implementation.md`; actual conversation exported
to `ai-logs/opencode/session-01-transcript.json` (raw service export of
session ses_e52dfae70ffe2kTxngyH7TDTD0, captured before this turn's final
response; all records as recorded, none fabricated). No challenge data, answer or
checker access, no model/API calls, spending, installs or downloads. H1 gate 4
is now unblocked for a full acceptance rerun; a full rerun and any live pilot
still require explicit user approval. H2 not started.


## 2026-11-06 - OpenCode Session 02 - final no-spend H1 closure

Full Linux acceptance rerun ONCE with the managed Ubuntu CPython 3.9.25:
`python3.9 -B -S tests/linux_acceptance.py --report
ai-logs/opencode/session-02-linux-acceptance.json`. All ten scenarios PASS
(launcher_hang 137 @ 13.09s, interrupted_write 124 @ 12.26s, launcher_success
0; every case zero leftover run-owned processes; before==after output hashes
on all incomplete runs; packaging probe "six modules with -S" recorded; uutils
coreutils 0.8.0 environment). This plus the focused Session-01 tests closes
the original gate-4 BLOCKING finding under uutils.

Complete Ubuntu unit suite ONCE (`python3.9 -B -m unittest discover -s tests
-v`, via a capturing wrapper that runs the recorded command as a child): 245
tests, OK, exit 0 (~46s). First wrapper attempt ran the suite in-process;
the real-spawn worker tests re-executed the wrapper and two hit the intended
worker deadline - tooling artifact, corrected, disclosed; the artifact run is
preserved verbatim in the archived conversation, the log file contains only
the valid rerun. Display-name renaming regression now established on Ubuntu 3.9.25.

Production hashes: data/llm/tasks/validation/solution identical to the
Session-10 recorded probe values; reasoning.py identical to the Session-11
post-Stage-E/F recorded value (5aadbde9...); six probed modules unchanged.
Only OpenCode-modified production file remains run.sh (Session 01).

Section 11a: gate 4 set PASS with fresh evidence; gates 1/2/3/5 standing PASS
(unit suite rerun included); gates 6/7/8/9 remain BLOCKED approval-dependent
(pilot cap, dataset metadata, verified pricing, explicit full-run approval).
H1 is NOT complete. Consolidated report:
`ai-logs/opencode/session-02-h1-final-report.md`. Estimates: input-only
method stands in session-13-h1-readiness.md; actual window counts, language
mix and verified model pricing remain unavailable without authorization.

Archives: session-00 (Plan session ses_e52e01d67ffeu9Cb3sEyBWIRiP) and
session-01 (build session pre-compaction snapshot, raw preserved byte-exact)
plus live session-02 continuation stored under `ai-logs/opencode/` with
deterministic Markdown renderings, verification stats and INDEX.md. Session-02
raw export was captured while the final consolidation response was still being
produced, so a genuine post-response refresh of session-02-h1-* is the sole
remaining archival action (commands recorded in INDEX.md; never touches
session-00/01 files). No challenge data, answers, checkers or check.py, no
API calls, spending, installs or downloads; prior Codex records untouched.
H2 not started.


## 2026-11-08 - OpenCode Session 07 - pilot model final switch to gemini-3.5-flash-lite

User-directed final preparation inside one Build session: pilot model changed
from `gemini-3.8-flash` to exactly `gemini-3.5-flash-lite`; approved pilot
design unchanged (25 base requests, 5 recoveries, 30 transmissions, 250,000
tokens, 600 s network deadline, USD 2.00 internal paid-equivalent safeguard,
four synthetic fixture packs only, no architecture changes). Free-tier limits
respected, billing not enabled: 15 RPM / 250K TPM / 500 RPD - the 30-transmission
envelope, serialized dispatch and 250k reservation fit all three; existing
429/Retry-After backoff handles per-minute throttling.

`VERIFIED_PRICING` refreshed from the current official Google pricing
documentation (retrieved 2026-11-08): `gemini-3.5-flash-lite` Standard paid
rates $0.30/Mtok input, $2.50/Mtok output (thinking tokens included), caching
$0.03; Free tier "Free of charge". Conservative projection over the whole run
envelope at paid rates: about $0.16 worst case, far inside the USD 2.00
safeguard.

Files modified: `tests/pilot_runner.py` (VERIFIED_PRICING model/source/rates),
`tests/test_llm.py` (temperature-regression pilot-path probes moved to the new
model; family case-insensitivity probe unchanged), `WRITEUP.md` (honest verified
state, within two pages), this appended checkpoint entry, `ai-logs/opencode/
INDEX.md` (Session 07 row), `ai-logs/opencode/session-07-export.py` plus its
two generated artifacts. `llm.py` was NOT changed: the approved family-prefix
check `chosen.lower().startswith("gemini-3")` already covers
`gemini-3.5-flash-lite`; the offline wire-body probe confirmed the
`temperature` key is omitted for the new model, and the updated
`test_default_temperature_is_model_specific` regression covers the pilot model
explicitly, explicitly-set values, and the environment path.

Verification (Windows 11 / CPython 3.12.9, project cwd, offline):
`python -B -m unittest discover -s tests -p test_pilot_runner.py -v`:
13 tests, OK (0.374s). `python -B -m unittest discover -s tests -v`:
**285 tests, OK (15.292s)**, zero failures/errors/skips. Production read-only
recomputation with `load_input`/`build_windows`/`window_packet`/`_encoded`/
`Budget`: per-window reservations 6,187 / 3,677 / 7,335 / 3,759 / 7,445 /
3,770 / 6,169 / 3,666 tokens; base-pass extraction charge 42,008 of 250,000
tokens (207,992 remaining); worst case each window using all three allowed
transmissions 126,024 tokens, projected USD 0.160687. Synthetic-only
configuration re-verified (PACK_ORDER = the four packs on disk; no path to
original conversations); envelope constants unchanged.

Session 07 archive (this session, `ses_e451f3c10ffevv4SLxROhjwYJp`, "Gemini
pilot preflight checks", created 2026-11-08): genuine raw export and
chronological transcript at `ai-logs/opencode/session-07-export.json` and
`ai-logs/opencode/session-07-transcript.md`, generated by
`ai-logs/opencode/session-07-export.py` from the local OpenCode store (same
mechanism and archival rules as session-06-export.py; hidden reasoning,
synthetic records and idle bookkeeping excluded from Markdown; long values cut
at 20,000 characters with markers; credential-shaped strings redacted).
Sessions 01-06 archives untouched.

Pilot execution status: **NOT YET RUN** - no live API call was made in this
session, per instruction. Remaining steps before Gate 6: (1) the user runs the
final PowerShell command in their own terminal with their own credentials
(LLM_MODEL=gemini-3.5-flash-lite, evidence path
`ai-logs/opencode/session-07-gate-6-pilot-evidence.json`); (2) evidence-file
envelope verification against `session-07-gate-6-pilot-evidence.json`; (3)
separately approved Gate 7 manual semantic review against the independent
expected matrix. Gate 8 needs pilot usage/latency plus authorized input-only
remaining steps before Gate 6: (1) the user runs that command manually;
(2) evidence-file envelope verification against
`session-08-gate-6-pilot-evidence.json`; (3) separately approved Gate 7 manual
semantic review. Gate 8 still needs pilot usage/latency plus authorized
input-only metadata; Gate 9 remains a separate full-run approval. H2 not
started.


## 2026-11-09 - Session 08 continuation - stdin-launch failure diagnosed; real-file launcher correction

The user manually ran the Session 08 Gate 6 command on 2026-11-08 19:55Z and
pasted the output. Diagnosis (analysis + offline reproduction only; no
production code changed for the diagnosis):

- Every transmission ended `worker_failure`; all 13 spawned HTTP workers died
  at process spawn before any network code. Root cause: the command piped the
  runner into `python -B -S -`; Windows multiprocessing `spawn` children try
  to re-import `__main__` from its file path `_fixup_main_from_path("<stdin>")`
  and raised `OSError: [Errno 22] Invalid argument` (child exitcode 1),
  13 times. **No Gemini API request was sent; no token usage or spend
  occurred** (self-consistent with telemetry: model null, reported tokens 0,
  unknown_usage 13 conservatively retained, dollar_cost null).
- The safety envelope behaved exactly as designed: 8 extraction jobs, 13
  transmissions = 8 originals + 5 recoveries (three-transmission cap per job,
  shared 5-recovery budget exhausted), tokens 69,071 <= 250,000, elapsed 1.36
  s <= 600 s; all downstream stages stayed explicit `incomplete` without
  dispatching or fabricating output; `envelope_verified: true`;
  `run_state: "completed"` means the loop terminated, not success. Offline
  reproduction by trivial stdin probe reproduced the identical Errno 22 +
  exit 1; a real-file probe produced child exit 0.
- Failure-run evidence preserved unchanged under a new name (verified before/
  after copy, SHA-256
  `3d79bc1e1a75d57eeb787950143540f43f6e976f6299ef8ed2e75cea2ba6829e`):
  `ai-logs/opencode/session-08-gate-6-stdin-launch-failure-evidence.json`.
  The original evidence path stays the live target for the next run.

Smallest launcher correction, approved pilot design unchanged (25 base / 5
recoveries / 30 transmissions / 250,000 tokens / 600 s / USD 2.00 safeguard /
four synthetic packs; no model, budget, billing or architecture change):

- Created `pilot_launch.py` at the project root (none of the six production
  modules edited): standalone real-file launcher with
  `if __name__ == "__main__":` guard so spawn children re-import inertly;
  reads LLM_BASE_URL / LLM_API_KEY / LLM_MODEL from the inherited
  environment with presence-ONLY checks (no value printed/logged); requires
  LLM_MODEL to be exactly `gemini-3.5-flash-lite`; calls the unchanged
  `tests/pilot_runner.run_pilot`/`VERIFIED_PRICING` real-mode path with
  `provider_controls_confirmed=True` (the standing user Free-Tier/no-billing
  attestation) and writes evidence to
  `ai-logs/opencode/session-08-gate-6-pilot-evidence.json`.
- `--spawn-check` mode: harmless no-dispatch verification (trivial module
  child, plus the production ProcessTransport against a reserved `.invalid`
  endpoint with a synthetic non-credential; the child executes the real
  worker path and returns the structured `network` error over the IPC
  buffer - the precise inversion of the stdin failure where children died
  with `worker_failure`).
- Added `tests/test_pilot_launch.py` (4 focused tests): missing-environment
  refusal without dispatch or stdout leakage; exact-model refusal without
  dispatch; verified-pricing/provider-controls/evidence-path pass-through;
  real-file spawn regression via the harmless probe.

Verification (Windows 11 / CPython 3.12.9, project cwd, offline; no live
API call was made in this session either):
- `python -B -m unittest discover -s tests -p test_pilot_launch.py -v`:
  **4 tests, OK, 0.262s, exit 0** (first run had 1 error: the mocked
  run_pilot recorder returned a MagicMock that the launcher's JSON summary
  serializes; corrected by returning a real dict in the test - correction
  contained to the test).
- `python -B .\pilot_launch.py --spawn-check` (the exact standalone command):
  module child exitcode 0; transport_events start/reaped; transport error
  code `network`; `child_executed_worker: true`;
  `spawn_from_real_file_ok: true`; exit 0.
- `python -B -m unittest discover -s tests -v`: **289 tests, OK, 14.113s,
  exit 0** (285 previous + 4 launcher tests).

Session-08 transcript refreshed: the exporter re-run now includes the
failure-output exchange, the diagnosis, this correction and the final
command (`session-08-export.py` -> `session-08-export.json` /
`session-08-transcript.md`; Sessions 00-07 untouched).

Remaining steps before Gate 6 (unchanged, user-supplied credentials only):
1. Optionally `python -B .\pilot_launch.py --spawn-check` (offline,
   credential-free). 2. In the user's own terminal, set the three
   environment variables and run `python -B .\pilot_launch.py`. 3. Agent
   verification of the evidence envelope. 4. Separately approved Gate 7
   manual semantic review. Gate 8/9 remain separate. H2 not started.


## 2026-11-08 - OpenCode Session 08 - model-switch re-verification and final pilot handoff

User-directed single Build session (`ses_e43a362cbffepcSxbg3AicXOd0`,
"Session 08 Gemini Flash-Lite pilot preparation"): evaluate the proposed
Gemini Flash-Lite alternative against Google's OFFICIAL documentation without
assuming the Session 07 model ID/pricing, then offline validation, final
PowerShell command, mandatory transcript archival, checkpoint closure.

Verification performed by fetching the official pages (pricing, the
`gemini-3.5-flash-lite` model page, rate limits, and the what's-new API-changes
guide) in-session:
- Exact stable model code confirmed: `gemini-3.5-flash-lite` (no preview
  suffix; "Stable" badge on the models page).
- Free tier: input and output "Free of charge"; no billing activation, no
  paid fallback. NOTE for the Free tier: context caching is NOT available
  (paid $0.03/Mtok) - the pilot uses no provider-side caching, and the
  run-local cache in `llm.py` is unaffected.
- Structured output: supported per the model page; the pilot sends
  `response_format {"type": "json_object"}` only.
- Standard paid rates confirmed UNCHANGED: $0.30/Mtok input, $2.50/Mtok
  output (thinking tokens included). VERIFIED_PRICING rates stand.
- Temperature officially "deprecated and ignored" for this model; requests
  must remove it. `llm.py` already omits the key for `gemini-3`-prefixed
  models: behavior confirmed correct, `llm.py` NOT changed.
- Honest caveat: the rate-limits page no longer publishes per-model Free-tier
  RPM/TPM/RPD and defers to AI Studio; the recorded planning quotas
  (15 RPM / 250K TPM / 500 RPD) remain the working assumption, and the
  serialized 30-transmission envelope plus existing 429/Retry-After backoff
  absorb per-minute throttling either way (transmission-cap stop is honest).

Approved pilot design UNCHANGED: 25 base requests, max 5 recoveries, max 30
transmissions, 250,000-token budget, 600 s network deadline, USD 2.00 internal
paid-equivalent safeguard, four synthetic fixture packs only, architecture and
module boundaries untouched. Conservative projection over the entire envelope
at the output rate (126,024 tokens x $2.50/Mtok = USD 0.315) stays far inside
the safeguard; the run-internal projection records about USD 0.161.

Files modified this session:
- `tests/pilot_runner.py` - VERIFIED_PRICING source re-documented (Session 08
  re-verification, both official URLs) and a `verification` documentation block
  added (model code, free tier, structured output, temperature, caching,
  rate-limit caveat). Normalized rates unchanged: 0.30/2.50 USD/Mtok.
- `WRITEUP.md` - verified state (model code, structured output, temperature
  deprecation, quota caveat), still within two pages.
- `ai-logs/opencode/INDEX.md` - Session 08 row plus the approved final
  PowerShell command.
- `ai-logs/opencode/session-08-export.py` (new) plus its two generated
  artifacts `session-08-export.json` / `session-08-transcript.md` below.
- This appended checkpoint entry. Sessions 00-07 logs/archives untouched;
  `llm.py` and all production modules untouched.

Verification (Windows 11 / CPython 3.12.9, project cwd, offline, actual):
- `python -B -m unittest discover -s tests -v`: **285 tests, OK, 8.916s,
  exit 0** (also 285 OK pre-change baseline). Pilot-runner 13 OK (0.231s),
  pilot-harness 14 OK (0.014s), test_llm 57 OK (2.066s, includes the
  temperature-omission regression for the pilot model: `-k temperature`
  exit 0).
- Configuration probe: `count_plan()` planned 25 base calls (EX 8 / ORG 2 /
  ENT 3 / GOALS 2 / interpret 7 / match 2 / HELP 1); PilotLimits validate()
  passes with max_transmissions 30, max_recoveries 5, base_calls 25,
  token_reservation 250000, spend_ceiling_usd 2.00, network 600 / finalize
  750 / overall 780 s; `normalize_pricing(VERIFIED_PRICING)` passes
  fail-closed checks; fixture root is `tests/pilot_fixtures` with exactly the
  four packs pilot_en, pilot_hi, pilot_bn, pilot_hn on disk (synthetic-only).
- No live API call was made in this session. Pilot execution status:
  **NOT YET RUN**.

Final PowerShell command (recorded verbatim in INDEX.md and in the Session 08
transcript): the one from the Session 07 handoff updated to write evidence to
`ai-logs/opencode/session-08-gate-6-pilot-evidence.json`, running
`pilot_runner.run_pilot(mode="real", verified_pricing=VERIFIED_PRICING,
provider_controls_confirmed=True, ...)`. The user supplies LLM_API_KEY locally
in their own terminal; no script here ever requests, prints, logs, or commits
a key.

Remaining steps before Gate 6: (1) the user runs that command manually;
(2) evidence-file envelope verification against
`session-08-gate-6-pilot-evidence.json`; (3) separately approved Gate 7 manual
semantic review. Gate 8 still needs pilot usage/latency plus authorized
input-only metadata; Gate 9 remains a separate full-run approval. H2 not
started.


## 2026-11-09 - Session 08 continuation - real-file pilot ran; extraction quality correction

The user ran the corrected real-file launcher on 2026-11-08 20:16Z. Windows
spawn now works: 8 real Gemini extraction dispatches on
`gemini-3.5-flash-lite`, 14,650 provider-reported tokens (5,877 prompt /
8,773 completion), zero unknown-usage attempts, envelope_verified true. Two
successes (window-5 jobs of pilot_hi/pilot_hn, finish stop, 167/169
completion tokens), four `truncated` (every window-0 job of all four packs at
completion 2044 against the 2048 wire cap), two `validation` failures
(window-1 jobs of pilot_en at 84 completion tokens and pilot_bn at 177).
Downstream stages stayed explicitly `incomplete` without dispatch or
fabricated output. Run evidence: `ai-logs/opencode/session-08-gate-6-pilot-
evidence.json`; preserved unchanged under
`ai-logs/opencode/session-08-gate-6-real-launch-partial-run-evidence.json`
(SHA-256 identical before/after copy:
`1079ac05c0724844b78fae76a9135dd06089f65457959e6d170ac8a499d3bd5e`).

Diagnosis from evidence + production code (no response bodies are retained by
design, so validator mismatch modes are inferred conservatively):

- Truncations: `pilot_runner._dispatch_window` sent `max_tokens=2048`, but the
  real tokenization of a full window's covered+observations JSON exceeds it
  (all four window-0 jobs cut at 2044/2048, `finish_reason "length"` ->
  `llm.py` classifies `truncated`, which is non-retryable by design).
  Entities/goals stages already use 4096, so extraction was the outlier.
- Validation failures: clean JSON, `finish_reason` stop, short responses
  (84/177 tokens) rejected by `reasoning.validate_extraction` because it
  demanded `covered` equal, in ORDER, the exact `asdict(MessageSpan)` list
  (three int-keyed fields per span). A multi-primary window whose packet
  order is not message-id order (pilot_hi/bn/hn pack pipelines fail this
  way offline too), packet-echo extra keys (the packet's primary entries
  carry text/sender_id/ts/kind/quoted_id), or offset type representations
  could each produce such a rejection; exact mode per job is not recoverable
  post-run.

Verification BEFORE changing limits — 25-job schedule and reservation
(extraction prompt estimates sum 25,624 from the real telemetry; offline
byte-proxy estimate for ALL 25 planned jobs is 26,552):
- extraction base charge with cap 4096: 25,624 + 8x4096 = 58,392
- extraction worst incl. 5 recoveries: 25,624 + 13x4096 = 78,872
- absolute worst: 30 transmissions all at the 4096 cap + all 25 prompt
  estimates = 149,432 < 250,000 (headroom 100,568)
- USD bound: even the full 250,000 at the $2.50 output rate = $0.625 < $2.00

Smallest corrections (no architecture/model/budget change; approved envelope
unchanged):
1. `tests/pilot_runner.py`: extraction dispatch cap 2048 -> 4096 (pilot
   scope; production `extract_windows` default stays 2048), with failure-
   code recording that surfaces the REAL LLMError codes (`truncated`,
   `validation`, ...) instead of generic `request_failed`.
2. `reasoning.py validate_extraction`: covered compared as an exact
   order-insensitive multiset (BOTH sides sorted with one key), packet-echo
   extra keys dropped before comparison, and int-valued string/float
   offsets coerced for covered AND evidence items; evidence offsets are
   normalized in the returned observations so downstream always sees ints.
   Containment in supplied spans and the byte-exact text match are
   unchanged; duplicates/partial coverage/wrong/out-of-span evidence still
   rejected. First relaxation attempt compared a sorted expected list
   against packet-ordered covered and wrongly failed pilot_hi/bn/hn offline
   pipelines — caught by the full suite, fixed by sorting both sides.
3. `EXTRACTION_PROMPT`: one clarification line (covered entries carry
   exactly {message_id,start,end}; evidence offsets are original-body
   character offsets).
4. `pilot_launch.py`: EVIDENCE_PATH now points to the NEW
   `session-08-gate-6-pilot-retry-evidence.json` so no prior evidence is
   ever overwritten; docstring updated.

New regression tests `tests/test_extraction_quality.py` (11 tests):
covered order/extra-keys/numeric-forms accepted; multi-span window whose
packet order is not id order accepted; duplicates, partial coverage,
wrong/out-of-span, boolean and fractional offsets still rejected; offline
pilot reproduces all-truncated and all-validation runs with the real codes,
exactly one transmission per failed job, zero recoveries, every downstream
stage explicitly incomplete and no fabricated output; dispatch wires carry
max_tokens 4096; envelope/USD bound arithmetic asserted.

Results (Windows 11 / CPython 3.12.9, offline only):
- `python -B -m unittest tests.test_extraction_quality -v`: 11 tests OK.
- Full suite `python -B -m unittest discover -s tests -v`: **300 tests, OK,
  20.930s, exit 0** (289 prior + 11 new). Intermediate full-suite runs
  surfaced and fixed the relaxation-side bug described above.

Next bounded live attempt (user's terminal only; no live call from here):
set the three environment variables and run `python -B .\pilot_launch.py`,
which now writes `session-08-gate-6-pilot-retry-evidence.json`. The stdin-
superseded command and the first real-file attempt stay preserved. Gate 7
manual semantic review remains a separate approval. H2 not started.

## Session 08 Build (2026-11-09) - downstream diagnosis + honest corrections from the real retry run

Source of truth: `ai-logs/opencode/session-08-gate-6-pilot-retry-evidence.json`
(created 2026-11-09T06:10:59Z; preserved unchanged). Facts: run_state
completed, envelope_verified true, planned 25, dispatched 20 jobs / 21
transmissions, charged 35,372 tokens (3,987 reserved conservatively for 1
unknown-usage attempt), elapsed 73.657 s of 600 s, projected USD 0.203 of
2.00, 1 recovery of 5. All 8 extraction windows succeeded. Downstream: 9 of
12 dispatched jobs failed (5x `validation`, 4x `malformed_content`); 3
succeeded (pilot_bn organisations - a VALID empty envelope, pilot_en goals,
pilot_hi task-interpret with one honest unresolved item).

Failure-to-root-cause map (exact job IDs in the evidence telemetry; response
bodies are NOT retained by design - exact failure shapes AND the Bengali HTTP
status were unrecoverable, disclosed rather than reconstructed):
- `validation` (5): pilot_en/organisations (90 tok), pilot_hi/entities (540),
  pilot_bn/entities (1895), pilot_en/task-review x2 (86, 138 tok). Parsed
  dict rejected by the stage validator -> evidence-driven contract
  deviations; correction is diagnostics only (see below), no loosening.
- `malformed_content` (4): pilot_en task-review x1 (153 tok), pilot_hi/goals
  (247), pilot_hn task-review (93), pilot_bn task-review (99 tok, whose
  attempt 1 was a transient HTTP failure). finish-stop content failed the
  strict JSON-object parse under `response_format json_object` - likely
  fence/prose wrapping; no validator changed, only ONE balanced {...} unwrap
  in the shared parse path.
- Bengali transient HTTP: recovered exactly as designed (1 of 5 recoveries,
  unknown usage conserved). No behaviour change.

Five planned jobs not dispatched (25 planned vs 20 dispatched):
1. pilot_en/entities - gated by the incomplete English organisations stage.
2. pilot_en/help - all English task interpretations failed, so no open tasks
   existed; the five-array candidate is invalid without open tasks and the
   stage recorded its explicit prerequisite-gated failure with NO dispatch.
3+4. pilot_en/match and pilot_hn/match - no successfully interpreted events
   survived to matching.
5. One pilot_hn/task_interpret - interpretation dispatch is
   observation-driven and the real extraction produced only one sampled
   offline-planned observation; the offline plans are estimates, telemetry
   records actuals (also why pilot_bn/task_match never dispatches offline:
   pilot_bn has no sampled interpretations).

Smallest corrections (approved architecture, module boundaries, model, and
the full 25-request envelope unchanged):
1. `validation.py`: `read_json` strict parse first; on failure, ONE balanced
   outermost {...} (string-aware scanner) is extracted and re-parsed under
   the SAME strict rules (duplicate keys, non-finite constants,
   non-object payloads still rejected). New `_outermost_object`.
2. `llm.py`: `Client._validate` now uses the shared `read_json`
   (new acyclic `llm -> validation` import edge; validation.py is
   stdlib-only) and the `validation` LLMError detail names the local
   exception class only. Per-transmission HTTP status persisted:
   `Budget.settle` gained a status argument and records an integer-only
   `http_status` (closing the Bengali-run status loss).
3. `reasoning.py`: raw-JSON-only requirement lines added to CONTEXT_PROMPT
   and the task-review prompt; `CONTEXT_VERSION` "context-2" -> "context-3",
   task-review "task-review-1" -> "task-review-2" (versioned cache keys, no
   loosening).
4. `tests/pilot_runner.py`: failed jobs record safe local `error_detail`
   and `http_status`; transmission entries now carry `http_status`.
5. `pilot_launch.py`: EVIDENCE_PATH -> NEW
   `session-08-gate-6-pilot-retry-2-evidence.json`, and `launch()` refuses
   BEFORE any dispatch when the target evidence file exists (preserved
   evidence can never be overwritten).

New offline regressions:
- `tests/test_stage_quality.py` (16): read_json tolerance AND strictness
  (fences/prose recovered; duplicate keys, NaN, non-objects, prose-only
  rejected; braces inside strings skipped); llm._validate accepts
  fenced/wrapped objects, keeps non-objects `malformed_content`, and surfaces
  the local class name in `validation` details without leaking credentials;
  help dependency fails closed without dispatch; full offline pilot runs:
  25-for-25 planned dispatch accounting and envelope verification; transient
  500 -> exactly one retry+recovery with per-transmission HTTP status 500;
  all-malformed interpretations (7 jobs, no retries/recoveries, no match
  dispatch, 4 incomplete task stages, en help failure with no help dispatch
  = the real-run replica); an invalid organisation envelope that gates
  pilot_en entities with zero dispatch and an explicitly incomplete state;
  raw-JSON prompt/version bumps; valid + invalid task-interpretation events
  (TaskError for create/update/evidence/details rejections).
- `tests/test_pilot_launch.py` (+1): an existing evidence target refuses the
  whole launch pre-dispatch, leaves the file byte-identical, zero runs.

Verification (Windows 11 / CPython 3.12.9, offline only):
- `python -B -m unittest tests.test_stage_quality -v`: 16 OK, exit 0.
- Full suite `python -B -m unittest discover -s tests -v`: **317 tests, OK,
  17.307s, exit 0** (was 300; +16 stage-quality +1 launcher).

Gate 6 status: NOT PASSED. The envelope itself verified (21<=30
transmissions, 1<=5 recoveries, 35,372<=250,000 tokens, 73.657<=600 s,
USD 0.203<2.00; synthetic-only confirmed), but 9 of 12 downstream dispatches
failed and the extraction-window corrections exist only in the first real
run's window scope. Next live run requires separate explicit user
authorization and a fresh evidence filename; `pilot_launch.py` now targets
`session-08-gate-6-pilot-retry-2-evidence.json` and refuses to overwrite.
Gate 7: not ready for full semantic review (only extraction-window real
outputs exist); extraction-window review may proceed meanwhile. Sessions
00-07 and all prior evidence files untouched.

## Session 08 Build (2026-11-09, second Build session) - bounded privacy-safe response capture + documentation completion

Prepared for the next bounded Gate 6 run: every settled attempt will now
record ONE bounded, response-side capture so future `validation` vs
`malformed_content` failures are precisely diagnosable from files and Gate 7
semantic review can use the actual structured model text.

Evidence preservation (verified, untouched, SHA-256):
- `session-08-gate-6-stdin-launch-failure-evidence.json` 13,038 bytes,
  SHA-256 `3d79bc1e1a75d57eeb787950143540f43f6e976f6299ef8ed2e75cea2ba6829e`.
- `session-08-gate-6-real-launch-partial-run-evidence.json` 10,837 bytes,
  SHA-256 `1079ac05c0724844b78fae76a9135dd06089f65457959e6d170ac8a499d3bd5e`.
- `session-08-gate-6-pilot-retry-evidence.json` 20,840 bytes, SHA-256
  `0ce77f58c10901f89af7bb3c439bd2af516cdd26b5792d45658a9d819de5f48f`.
None of these (nor any Session 00-07 artifact) was overwritten.

Capture seam (minimal, opt-in, response-side only):
- `llm.py`: `Client(transport=..., capture=None, capture_max_bytes=4096)`.
  After each settled attempt, `_capture` emits ONE record: `job_id`,
  allowlisted cache-context identifier fields (stage, prompt_version,
  schema_version, fingerprints, timezone_policy, as_of - everything else
  dropped), attempt/recovery/retry flags, settled outcome code, HTTP status,
  finish_reason, model, safe local `error_detail`, capped body (`body_bytes`
  exact uncapped length, `body_sha256` of the UNCAPPED response,
  `body_truncated`, capped `body_text`) and capped `content_text`. Provider
  error pages for non-2xx are NEVER captured (only status + local code).
  NEVER captured: request/wire bodies, transport headers, endpoint,
  credentials. Capture callback failures count (`capture_failures`) and
  never affect dispatch. Default capture=None keeps prior behavior.
- `tests/pilot_harness.py`: PilotHarness forwards `capture`/`capture_max_bytes`
  to its Client. `tests/pilot_runner.py`: `run_pilot(..., capture_path=None,
  capture_max_bytes=4096)` collects captures, adds an additive
  `response_captures` summary to the evidence document, refuses pre-dispatch
  when the capture file exists (`capture_exists`) or when capture/evidence
  paths collide (configuration), and writes the separate capture artifact
  (same JSON guarantees as evidence; `synthetic_only: true`).
- `pilot_launch.py`: the single approved launch now targets
  `session-08-gate-6-pilot-retry-2-evidence.json` PLUS
  `session-08-gate-6-pilot-retry-2-captures.json` and refuses before ANY
  dispatch when either file already exists (`target_exists`).

Observation-driven dispatch documentation (no invented jobs): the
`tests/pilot_runner.py` docstring now states explicitly that the TASK-stage
planned counts are planning estimates - interpretation dispatches are the
task_create/task_update observations the REAL extraction produced for the
sampled stable message IDs, the runner never fabricates events to reach 25,
and the real retry run's 6-of-7 interpretations plus 0 matches/1 help gate
were the correct by-design results of prerequisite incompleteness.

Preserved unchanged: production schemas, validators, prompts, stage
contracts, module boundaries, approved envelope limits (25 base / 5
recoveries / 30 transmissions / 250,000 tokens / 600 s / USD 2.00 safeguard /
four synthetic packs), model `gemini-3.5-flash-lite`, and the corrected
downstream-quality changes from the first 2026-11-09 Build session.

New offline regressions:
- `tests/test_response_capture.py` (14): default capture=None; success
  capture fields (outcome/finish_reason/model/attempt/flags/body bytes);
  request-side sentinel, API key, endpoint and "Authorization" never in any
  capture; strict byte cap with FULL uncapped SHA-256 + exact byte length;
  `malformed_content` and `validation` outcomes captured with safe local
  details; HTTP error pages never captured while status is recorded;
  retry flags across a 429-then-success pair; a failing capture sink never
  breaks dispatch (counted failure); cache-context allowlist (secret and
  nested fields dropped); full offline mock run captures one record per
  settled transmission (25/25) with artifact redaction, never-overwrite
  refusal pre-dispatch without a single transport call, and the
  capture/evidence path-collision refusal.
- `tests/test_pilot_launch.py` (+1): existing CAPTURES_PATH also refuses the
  launch pre-dispatch with the file byte-identical; pass-through test now
  asserts the capture_path parameter.

Verification (Windows 11 / CPython 3.12.9, offline only):
- `python -B -m unittest tests.test_response_capture
  tests.test_pilot_launch -v`: 16 tests, exit 0.
- Full suite `python -B -m unittest discover -s tests -v`: **332 tests, OK,
  20.802s, exit 0** (was 317; +14 response-capture, +1 launcher).
- Windows spawn check `python -B .\pilot_launch.py --spawn-check`: exit 0
  (module child 0; transport events start/reaped; structured `network`
  error against the reserved .invalid endpoint; `spawn_from_real_file_ok:
  true`). No live API call was made.

Gate 6 status: unchanged, NOT PASSED (the capture work adds diagnosis
capability only; the real-run failures and their corrections stand). Next
bounded live run: user sets the three environment variables and runs
`python -B .\pilot_launch.py`; evidence goes to the fresh
`session-08-gate-6-pilot-retry-2-evidence.json` and captures to
`session-08-gate-6-pilot-retry-2-captures.json`, both refused if they
already exist. Gate 7 semantic review gains structured real response text
with identifiers once that run happens. H2 not started; Sessions 00-07 and
all previous evidence untouched.

## Session 09 (2026-11-10) — Final targeted repair session (OpenCode, offline)

Scope: the highest-priority problems from the 2026-11-10 audit. Offline only:
no live API call, no development-dataset inference, no dependency changes,
no architecture redesign. Pre-edit full backup verified byte-identical at
`C:\Users\Shalu Chauhan\AppData\Local\Temp\opencode\Xpert-Backup-20261110-190831\`;
all five preserved pilot evidence/capture artifacts hash-verified unchanged
before and after. Full details: `ai-logs/opencode/session-09-repair-session.md`
and the Session 09 section in `ai-logs/opencode/INDEX.md`.

Discovery: the repository already contained an UNDOCUMENTED third real pilot
run — `session-08-gate-6-pilot-retry-2-evidence.json` +
`...retry-2-captures.json` (2026-11-09T07:42Z; 18 transmissions, 68,313
charged tokens, 3 recoveries including one real 503 → recovery success,
envelope verified, synthetic-only, $0.20 paid-equivalent). **Gate 6: NOT
PASSED** by that run (9 worked/jobs failed across the dispatched set); this
entry closes the disclosure gap.

Root causes diagnosed from the captured response bodies (all synthetic packs):
1. extract (en): 3× transient HTTP 503 — bounded retry/recovery worked as
   designed; no defect.
2. extract (en): organisation NAME "HomeServe" used as a `subjects` entry →
   fail-closed `Unknown observation subject`. Prompt ambiguity.
3. goals (hi): one unquoted JSON key (`title:`) in an otherwise valid
   `json_object` reply → correctly `malformed_content`; unrepairable without
   weakening strict parsing.
4. entities (hi/bn): exact `{decisions}` envelope returned BUT extra
   top-level schema keys echoed (`people`, `organisations`, `chats`, `goals`,
   `open_loops`); bn also carried an evidenceless positive record (P04
   circle vendor). Both systemic contract ambiguities.
5. task-review (bn): observation hash cited as event `evidence` instead of a
   message ID → fail closed correctly.

Fixes (prompt/contract text + version bumps only; no validator, parser,
retry or token change; nothing provider-specific):
- `reasoning.py`: `EXTRACTION_VERSION` extract-1 → extract-2 (subjects must
  be exact packet person/chat IDs; names belong in `meaning`); `CONTEXT_VERSION`
  context-3 → context-4 (envelope exclusivity: never echo the supplied schema
  or add top-level keys beyond the contract's named keys; all JSON keys and
  strings must be double-quoted — no unquoted keys, single quotes, comments
  or trailing commas); entity contract (entity-3 text) requires nonempty
  evidence for every nonempty record unless the seed fixes its fields;
  task-review prompt task-review-2 → task-review-3 (evidence elements must be
  exactly message IDs present in the packet, never observation/hash IDs).
- `tests/test_pilot_launch.py`: the failing pass-through test now redirects
  BOTH launcher targets into a temporary directory (root cause: the preserved
  real retry-2 artifacts legitimately trigger `target_exists` before
  `run_pilot`, so call_count stayed 0). Production never-overwrite protection
  unchanged and verified; no evidence file deleted or modified.
- New `tests/test_capture_regressions.py` (10 tests): each captured shape
  replayed offline against production validators with anti-overfit controls
  (the envelope-only equivalent of the same decisions still succeeds; valid
  ID-subject extraction and message-ID task citations still validate);
  prompts asserted model-agnostic (no provider/model tokens).
- `tests/test_stage_quality.py`: version pins re-pinned to
  extract-2/context-4/task-review-3 plus contract-text assertions.

Verification (Windows 11 / CPython 3.12.9, offline only):
- `python -B -m unittest discover -s tests -v`: **342 tests, OK, 9.858 s,
  exit 0** (was 332 with 1 failure).
- `python -B -S tests/offline_readiness.py`: sparse fixture 599 fake calls/
  3.659 s; dense 765/40.183 s; both `succeeded`; identical output SHA-256;
  Python 3.9 grammar + imports passed.
- `python -B data.py ..\..\xpert-cold-start\data\dev`: succeeded; 138 chats,
  286 people, 4,502 messages (metadata only; answers/ never touched).

Status: **Gate 6 overall remains NOT PASSED and is not claimed.** The
corrected prompts (extract-2/context-4/task-review-3) are an evidence-based
hypothesis never yet run against a real model; no development-set evaluation
exists; semantic recall/precision remain unmeasured. One further authorized
bounded live run — targeting FRESH non-overwriting evidence/capture files
(the launcher correctly refuses the existing retry-2 artifacts) — remains
required before any Gate-6 accuracy claim; H2 remains separate. Sessions
00-08 and all prior evidence untouched.

## Session 10 (2026-11-10) — Corrected-prompt live validation (user-executed)

Offline launcher preparation first: optional fresh-destination override
(`PILOT_EVIDENCE_PATH` + `PILOT_CAPTURES_PATH`, both-or-neither; same
never-overwrite refusal re-applied to selected targets; defaults unchanged),
+3 focused tests; suite 345 OK; spawn-check `spawn_from_real_file_ok: true`.
Pre-edit backup `Xpert-Backup-20261110-192403` verified byte-identical.

Live run on `gemini-3.5-flash-lite`, four synthetic packs
(`session-10-gate-6-validated-{evidence,captures}.json`): 15/25 jobs
dispatched, 20 transmissions ≤30, recoveries 5 = limit, charged 59,672 ≤
250,000 tokens, projected USD 0.2024 (Free $0), 102.5 s ≤ 600 s; provider-
reported 23,659 tokens (13,913 prompt / 9,746 completion); conservative
reservation 77,446 + 71,680; 5 unknown-usage attempts settled (36,013
reserved, 0 outstanding); envelope_verified true; synthetic_only true;
run_state completed. Extractions 7/8; en goals OK; bn organisations
succeeded_empty; bn entities succeeded with exactly `{decisions}`; bn
task-review honest-ambiguous; hn tasks succeeded_empty; en organisations +
2 en task packets failed validation (fail-closed); en help invalid_candidate
(documented); hi downstream and en/hi entities never dispatched (honest
prerequisite incompleteness).

Session-08 class verdicts: name-in-subjects RESOLVED; unquoted keys
RESOLVED (zero malformed_content in 20 attempts); envelope echo RESOLVED on
bn; evidenceless positive records RESOLVED on bn (entity-3 followed); task
hash-citations RESOLVED (all evidence = message IDs); 503s recurred 5x,
absorbed by bounded retry/recovery (5/5 recoveries).

New prompt-side gaps (fail-closed correctly): organisations `type` and task
`details.type` enumerations are not stated in the packet contracts
(model answered "organisation" / "task" / "request"); one Hindi window
failed strict evidence-text equality on a one-character Indic transcription
slip (दोपहर → दपोर). Fix direction: contract text + version bumps only, in
a separate user-authorized cycle.

**Gate 6: NOT PASSED** (documented criteria applied verbatim; no threshold
changed): integrity/envelope pass, but downstream did not finish or honestly
complete end-to-end (en stalled at organisations, hi at extraction; entities
evaluated only on bn). Gate 7 is reviewable offline only for the bn/goals/
extraction successes. H2/full-run/hidden-set NOT STARTED and remain separate
approvals. Full session report:
`ai-logs/opencode/session-10-live-validation.md`. Sessions 00-09 and all
prior evidence untouched (hashes re-verified post-run).

## Session 11 (2026-11-10) — Targeted contract repair + offline verification

Offline only; **NO LIVE MODEL CALLS MADE**; no Gate 6/7/H2 work; no dev or
hidden data access. Backup `Xpert-Backup-20261110-195133` verified
byte-identical before editing.

Both Session-10 contract gaps closed with authoritative schema values
(schema.json, cross-checked with check.py):
- Organisations record: `type` ∈ [company, residence, vacation home,
  workspace, society, school, other]; `side` ∈ [home, work] (enum has no
  null); `role` ∈ [owner, partner, helper, resident, parent, member,
  other] — now documented verbatim in the packet contract with "Never
  substitute an unlisted value or null for an enumerated field."
- Task create `details.type` ∈ [commitment, followup, deadline, question] —
  now documented in the task-review packet contract with "never substitute
  or invent another value".

Version bumps: `CONTEXT_VERSION` context-4 → context-5 (semantic-seam
banner); task-review-3 → task-review-4. Prompt/contract text ONLY: no
parser, validator, schema, budget, retry or runtime change; provider-neutral.

New `tests/test_contract_enums.py` (16 tests): every schema value documented
in both contracts; documented lists equal the schema enums exactly
(verbatim comma-joined — no omission or broadening); permitted-value
success controls (`company`, `other` end-to-end; all four task types);
captured-style plus generic unsupported values fail-closed; message-ID
evidence and unknown-owner rules intact; SchemaValidator asserted un-widened;
no provider tokens; version-consistency pins. `test_stage_quality` pins
re-pinned.

Verification: full suite **361 tests, OK, 12.308 s**; offline readiness
sparse 3.884 s / dense 39.194 s, both `succeeded`, identical output
SHA-256, python-3.9 grammar + imports passed; dev-loader metadata smoke
succeeded (138 chats, 286 people, 4,502 messages, no issues). All seven
evidence/capture artifacts (five Session-08, two Session-10) re-hashed
unchanged after every edit. Full report:
`ai-logs/opencode/session-11-contract-repair.md`.

**Gate 6: remains NOT PASSED and is not claimed** — the enumeration fixes
have never run against a live model. The next bounded live validation
(fresh evidence/capture destinations via the launcher override) requires
separate explicit user authorization. H2/full-run/hidden-set NOT STARTED.
Sessions 00-10 and all prior evidence untouched.

## Session 12 (2026-11-10) — Second live validation of the Session-11 contracts

User-executed bounded live run (authorization by running the launcher);
agent evaluation offline. Created 2026-11-10T14:35:40Z: 11/25 planned jobs
dispatched, 15 transmissions ≤30, 3 recoveries ≤5, 45,922 charged ≤250,000
tokens, projected USD 0.1548 (Free $0), 80.374 s ≤ 600 s; envelope_verified;
synthetic_only; completed. Provider-reported 19,005 tokens
(10,024 prompt / 8,981 completion); conservative reservation 55,036 +
55,296; 3 unknown-usage attempts settled (26,917 reserved, 0 outstanding).

The user's PILOT_* variables reused the relative `session-10-gate-6-
validated-*` names (root placement; preserved originals untouched); the
NEW run's files were relocated byte-identically to
`ai-logs/opencode/session-12-gate-6-validated-{evidence,captures}.json`
(SHA-256 85643B8EA963B2DF… / 18250D938436B8D4…).

Results: first-ever dispatch of the task-match and help stages; en task
creates ×2 used enumerated types (`followup`/`commitment`) — **Issue B
validated live**; extraction 4/7 windows succeeded. Pinned failures:
en window-1 cited `HomeServe` at wrong offsets (38:47 vs actual 51) —
strict provenance rejection; hi window-5 repeated the दोपहर transcription
slip (दपौर) — recurring model hazard; bn window-0 failed beyond the
4,096-byte capture cap (honest inconclusive); task-match `none` reply with
EMPTY evidence rejected — **new prompt-side gap** (validator requires the
source message always cited; fix direction: contract text + version bump
in a future authorized cycle); help epoch-style `remind_at` rejected by
the already-documented ISO rule — model compliance failure, fail-closed
correct. **Issue A (organisations enums) NOT exercised live.**

**Gate 6: NOT PASSED** (criteria applied verbatim; no threshold changed) —
deeper pipeline than ever but not honest-end-to-end; the next bounded
attempt is ready when authorized with genuinely fresh filenames. H2/
full-run/hidden-set NOT STARTED. All prior evidence untouched. Full
report: `ai-logs/opencode/session-12-live-validation.md`.
