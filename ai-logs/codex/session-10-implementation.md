# Session 10 — H1 offline readiness review

Offline checks completed; H1 readiness gates remain unmet. No production changes.
Linux supervision, actual Python 3.9 execution, live inference and full-run
feasibility are unverified. Stop for user review; no live work is authorized.

## Environment and commands

Working directory: `C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert\xpert-cold-start-starter\cold-start`.
Windows-11-10.0.26200-SP0, CPython 3.12.9, MSC v.1942, AMD64.

- `Get-Command python,python3,py,wsl,docker,bash -ErrorAction SilentlyContinue | Select-Object Name,Source`
  found Python 3.12, WindowsApps python3 alias, py, wsl and Git Bash; no Docker.
- `py -0p`: registered CPython 3.12.9 and Astral CPython 3.12.16 only.
- `Get-Command python3.9,python39,docker -ErrorAction SilentlyContinue | Select-Object Name,Source`:
  no matching commands. No usable Python 3.9 discovered; no installation attempted.
- `wsl --list --quiet`: WSL is not installed. This is not a Linux test.
- `python -B -c "import sys,platform; print(sys.version); print(platform.platform())"`:
  environment above.
- `& 'C:\Program Files\Git\usr\bin\bash.exe' -n run.sh` and
  `& 'C:\Program Files\Git\usr\bin\bash.exe' run.sh`: both failed before shell
  execution, exit -1073741502, cannot create signal pipe, Win32 error 5.
  Neither syntax nor usage exit codes were verified by these commands.
- `git status --short`: exit 1, not a Git repository. A repository diff is
  unavailable. Only the new harness and these records/checkpoint were edited;
  six production SHA-256 hashes printed by the probe matched across runs.

Linux distribution/interpreter, timeout utility, actual run.sh success/failure
codes, group cleanup, ignored TERM escalation, hung parent, and kill during
temporary writing remain untested. Windows spawn tests do not satisfy those gates.

## Exact test results

| Command | Result | Runtime | Exit |
|---|---|---:|---:|
| `python -B -m unittest discover -s tests -v` | 231 passed; 0 failures/errors/skips/hangs | 14.075s | 0 |
| `python -B -m unittest discover -s tests -p test_llm.py -v` | 56 passed; 0 failures/errors/skips/hangs | 2.646s | 0 |
| `python -B -m unittest discover -s tests -p test_solution.py -v` | 9 passed; 0 failures/errors/skips/hangs | 0.353s | 0 |
| `python -B -S tests/offline_readiness.py` (final) | six module imports/grammar checks, two volume assertions passed | per fixture below | 0 |

The probe parses all six production modules with `ast.parse(feature_version=(3,9))`
and imports them with site packages disabled. Required production dependencies
are standard-library/local modules; the probe also executes the complete pipeline
under `-S`. No third-party installation is needed for these observed paths.
Grammar/import success under 3.12 does not prove Python 3.9 runtime compatibility
or clean Linux packaging. Optional tokenizer/provider compatibility was not tested.

Failure checks include real spawned hang/partial-transfer termination and reap,
worker crash/empty result, retry/cutoff behavior, unknown usage, interrupted work,
every pipeline stage failing, invalid help, and deadline refusal before publication.
Real Windows hang tests assert nonzero worker exit, reap, unchanged active-child
set, and elapsed time below three seconds for a 1.2-second timeout. Kill escalation
uses a synthetic process object, not POSIX signals. Full-suite export tests cover
partial write/KeyboardInterrupt, flush/close/fsync/replace failures and changed
serialization, retaining original output. No test remained hanging.

## Synthetic volume results

New explicit harness `tests/offline_readiness.py` reuses the Stage G guarded fake
transport, blocking pipeline socket/DNS calls and restricting file reads/writes.
It creates and removes its own inputs: 15,000 messages, 60 group chats, one person,
3,000 messages in one chat, one 15,000-character message, 4,343,866 input bytes.
No challenge files are used. The mock budget explicitly plans 10,000 calls;
there is no provider. A fake clock controls application deadlines; perf_counter
measures actual elapsed pipeline time separately. Fixture creation is excluded.

| Final fixture | Seconds | Peak traced Python bytes | Fake calls | Pipeline outcome |
|---|---:|---:|---:|---|
| Sparse observations (four kinds from M1) | 6.589 | 34,595,896 | 599 | succeeded, all stages complete, valid output published |
| Dense person observations from every primary span | 15.055 | 74,426,040 | 594 | entities incomplete, exit 1, old output preserved |

The harness itself exits 0 because it asserts both successful sparse processing
and safe dense failure. Memory is tracemalloc peak allocation, not process RSS,
child memory or a memory limit. Instrumentation affects timing. Mock request
history is discarded to avoid test-only accumulation; production cache/results
remain enabled. Peak dispatched request was 14,312 bytes in both fixtures.

Measured dense entity context was 11,119,951 bytes, exceeding its existing
100,000-byte bound; no entity HTTP request was dispatched. Sparse entity context
was 11,329 bytes. Entity batches repeat all observations, cited full messages,
chats and schema. This is a demonstrated context-scaling bottleneck; batching
required IDs alone does not reduce that context. Packet limits safely fail closed.
No production defect was patched and no scaling redesign was attempted.

These fixtures represent message volume and long-span stress only. They have low
person/task/organisation diversity, zero model latency and fabricated usage.
They do not measure inference accuracy, provider capacity, real observation
density, realistic task matching cost or cost/latency forecasts. No 30-minute
guarantee follows. Actual deadline enforcement during a hung Linux parent remains
unverified, and direct Python execution has no outer hard-timeout supervisor.

## Harness development and changed files

The first probe invocation failed with a syntax error in the new harness; fixed
only that file. The second imported all modules but hit the reused small fixture's
30-call plan, safely preserving output (4.511s, exit 1). The harness then explicitly
configured its larger mock plan. Its first successful paired run measured sparse
6.934s/34,583,019 bytes and dense 13.144s/73,855,838 bytes, exit 0. Added packet-size
measurement and the dense-bound assertion, then ran the final results above.
These were harness issues, not production regressions; existing tests were unchanged.

Changed files: new `tests/offline_readiness.py`, this report,
`session-10-transcript.md`, appended `progress-checkpoint.md`.
No production modules, launcher, schema, previous reports or tests were changed.
No answer keys, actual checker, challenge dataset, real API, paid experiment,
downloads or installations were accessed/executed. Existing suite negative
controls use synthetic decoys only. No OS-wide network/filesystem trace is claimed.

Remaining: obtain an already provisioned Linux environment and supported Python
3.9 runtime for the outstanding offline gates; review the context-scaling result
before authorizing any implementation change. Live pilot and input-only planning
remain separately unapproved. Stop for review.

## 2026-11-05 - Session 10 addendum: dense-context diagnosis only

Status: root cause established; proposed implementation and verification PENDING
USER APPROVAL. H1 has not passed and the issue is not fixed. No production or
existing test files changed during this investigation.

### Construction path and measured cause

`extract_windows` validates original spans, hashes observations and merges exact
overlap duplicates, preserving `windows`. It returns observations in hash-ID order,
not chronological order. `resolve_entities` indexes ALL extraction kinds, creates
the required people/chat list, then batches only that list into groups of 32.
For every batch it builds the same full observation list, all canonical organisations,
all chats, full seed and schema, and every full original message cited by ANY
observation. `_call` serializes the entire packet before checking 100,000 bytes.
The size exception is caught and recorded as `entity_resolution_failed`; required
entities stay pending. No entity request is dispatched. Stage G refuses publication.

Read-only, in-memory instrumentation of the unchanged dense probe confirmed:

| First packet component (encoded value only) | Bytes |
|---|---:|
| observations | 6,888,357 |
| messages | 4,222,040 |
| schema | 3,513 |
| chats | 5,152 |
| organisations | 108 |
| required IDs | 510 |
| seed | 30 |
| contract | 144 |

JSON keys/separators account for the remaining bytes. Two batches (32 and 29
targets: one person and 60 chats) measured 11,119,951 and 11,119,900 bytes.
There are 15,006 distinct observation IDs, 15,006 evidence spans, 15,003 distinct
source spans and 15,000 distinct messages. Three repeated spans come from M1's
four different observation kinds; these are not redundant observations to delete.
Independent messages with identical wording must remain independent evidence.

Within observations, evidence arrays occupy 3,109,480 bytes and window-ID arrays
1,197,854 bytes (subcomponents, not additional totals). Quoted source text also
occurs in full message bodies; full bodies restore text outside extracted spans.
The messages dictionary already deduplicates by original message ID within a
packet. The problem is global evidence aggregation and repetition across batches,
not repeated dictionary keys or failed overlap deduplication. Each batch rebuilds
and reserializes this context; smaller target batches alone increase repeated work.
Increasing the cap only postpones failure. Removing full bodies and window arrays
alone still leaves about 5.70 MB before adding necessary source metadata.

Diagnostic command: PowerShell here-string piped to `python -B -S -`; exact Python
body is retained in the transcript. It temporarily wrapped `reasoning._call` in
memory to count components, then ran `probe.volume(dense=True)`. Exit 0: expected
incomplete entity result, prior output preserved, 594 fake calls. Instrumented
elapsed 21.830s, peak traced Python allocation 74,508,701 bytes. This is additional
diagnostic overhead, not a new performance baseline. No full-suite rerun was
needed for documentation-only changes; earlier 231-pass result remains historical.

### Recommended smallest safe scope

Keep the six modules, public resolver result, canonical organisation stage,
Stage D budget/client and final validation/export. Change only entity packet
planning, its versioned response contract and deterministic merge in reasoning.py,
plus focused synthetic tests after approval. The plan already requires compact
observations/relevant original evidence, bounded entity/chat partitions and review
of conflicts; no new service, module or unbounded summarization loop is needed.

1. Keep an immutable run-local evidence/provenance registry. Wire records carry
   original observation IDs, meaning/subjects, exact cited text/offsets and source
   metadata (message/chat/sender IDs, timestamp, quote references). Retain full
   messages and window IDs locally, referenced by original IDs. Include needed
   quoted/context spans explicitly and account for their bytes; do not silently
   truncate evidence or treat a compact projection as a complete original body.
2. Preplan deterministic byte-bounded evidence partitions and target batches.
   Preserve a coverage manifest linking required targets to every assigned evidence
   partition. Subjects, source chats, participants and quote/cross-chat links may
   conservatively route evidence; never drop unassigned/ambiguous observations or
   filter solely by observation kind. Fall back to bounded review for uncertain
   routing. The dense case still assigns all P1 evidence to P1, so evidence slicing
   is essential even with relevance routing. Shared context can serve several
   targets in a packet. Count schema/seed/metadata and JSON overhead before dispatch.
   An indivisible oversized evidence unit or fixed context stays explicitly
   incomplete; no recursive splitting or silent clipping.
3. Collect validated partition-level proposals, not independently final profiles.
   Require acknowledgement of partition/target coverage; distinguish no contribution
   from unresolved/failed inference. Validate citations against that partition's
   allowed original evidence. Missing partitions block final completion even when
   other partitions produced useful records. Keep the existing small-context path
   where possible; version any new prompt/cache contract.
4. Merge exact agreeing field proposals deterministically, union original evidence
   and provenance by ID, and preserve seed circles. Set-valued relationships may
   combine only when validated compatible; missing fields are not negative facts.
   Never choose a scalar/chat target by last response, majority count or recency
   alone. Conflicts require a bounded review of the competing original supports;
   if unresolved, over budget or over context, leave the target pending. Do not
   concatenate every partition's evidence into a new unbounded final request.
   Return one record per required ID only after all assigned work and final
   consistency/schema checks succeed. Existing failure/output safety remains.

Order evidence using Stage A's dated/undated ordering, timestamp and original
physical line, with message ID/span offsets/observation ID as stable tie-breakers.
Undated evidence stays in an explicit trailing partition, without guessed dates.
Do not regenerate source or observation IDs. Local registry joins preserve full
window provenance when wire packets omit those strings. Determinism applies to
partitioning/merging for the same validated replies, not fresh model behavior.

Preplanned partitions are declared base jobs, counted before dispatch; retries
and any recovery split children retain their original job lineage and existing
three-transmission/20% limits. Do not relabel failed-job retries as fresh partitions
to bypass Stage D. Budget/deadline exhaustion must still block completion.

### Expected impact, risks and approval tests

Current construction repeats O(total evidence + cited message bytes) work per
target batch. Index once, stable-sort once, then serialize bounded partitions;
cost follows actual evidence-to-target memberships, which can still be large.
Transient encoded entity packets would fall from about 11.1 MB to at most 100 KB
(over 100-fold smaller for that buffer), not for total process memory. Source
registry, extraction results, provenance and client cache remain O(input/work).
Accumulated cache/proposals may offset peak-memory savings; measure rather than
promise lower total RSS. Avoid quadratic trial-serialization of a growing packet.

Even the simple compact projection leaves megabytes: expect many additional
entity calls (potentially tens to hundreds, depending on routing/overhead), not
two. Current dense entity calls are zero because it fails before dispatch.
Successful dense processing therefore adds latency/work; no defensible seconds,
cost estimate or 30-minute guarantee is available without implementation and
separately authorized latency evidence. Relevance errors, cross-partition meaning,
conflicting temporal relationships and reducer overflow are principal risks.
Other global organisation/goal/help packet limits are unchanged and remain risks.

Required tests after approval:
- Existing sparse 15,000-message case still completes with unchanged validated
  output for equivalent mocks. Dense case completes under consistent partition
  mocks, every packet <=100,000 bytes, every target/evidence partition accounted
  for; keep a separate unavoidable-overflow case that remains incomplete.
- Original IDs, exact long-message spans/text, distinct identical-wording episodes,
  duplicate-window union and full local provenance survive planning/merging.
- Repeated runs and reordered input observations/reply arrival give identical
  plans, IDs, merged output/provenance; dated ties and undated sources are stable.
- Cross-chat person consistency, multiple organisations sharing a participant,
  group-to-person targets, seed circles and compatible relationships remain valid.
- Conflicting fields/targets, missing or null decisions, unknown/out-of-partition
  citations, failed middle partitions and oversized review remain incomplete.
- Timeout, retry/job limits, budget exhaustion and cutoff preserve original output
  bytes and clean owned temporary/worker resources. No incomplete-to-empty success.
- Re-run focused reasoning/integration tests, the offline probe and the complete
  documented suite; measure packet counts, timing and memory. Mock success is not
  a semantic-accuracy claim. Linux/Python 3.9 readiness remains outstanding.

Exact next steps, ONLY after approval: add failing partition/merge regressions;
implement bounded planning and versioned partition responses; add deterministic
merge/bounded conflict handling; adapt only the synthetic mocks needed for the
new contract; execute focused, sparse/dense and full tests; append actual results.
No implementation or verification of this proposal has occurred. Wait for approval.

## 2026-11-05 - Approved bounded entity implementation and verification

This entry supersedes the diagnosis-only pending status above. The user approved
the bounded entity fix, synthetic verification and records update. Implemented
and verified offline; H1 overall remains unmet and H2/live inference is unauthorized.

### Changed files and behavior

- `reasoning.py`: added deterministic entity packet planning and compatible record
  merging; changed only entity resolution. No other runtime module changed.
- New `tests/test_entity_partitions.py`: 13 synthetic regression tests.
- `tests/offline_readiness.py`: dense case now requires success, bounded packets,
  complete per-target evidence coverage and unchanged local registry; counts
  packets and compares sparse/dense final output SHA-256. Retained existing
  fixture volume/content, guards, imports and grammar checks. Existing Stage A-G
  unit tests and test_solution mocks were not changed or weakened.
- Appended this report, activity transcript and progress checkpoint; earlier
  entries remain historical, including the original expected dense failure.

Before production edits, the initial seven new tests ran: two passed, four failed,
one errored (missing conflicts result). Failures showed unbounded entity context,
missing partition/no-contribution behavior and hash rather than date ordering.
After implementation all seven passed; coverage was expanded to thirteen.

The entity-3 contract uses original observation IDs, meanings/subjects, exact
evidence text and original offsets, plus message ID/chat/sender/kind/quote-reference,
timestamp and physical-line metadata. Full original observations, including all
window provenance, remain in `evidence_registry`; full messages remain in InputData.
It does not reconstruct full message bodies from spans. Missing context that
prevents inference must return pending. Packet content changes invalidate existing
entity cache keys; unrelated prompt families were not changed.

Plan all partitions before dispatch. Sort by source timestamp with undated sources
last, then physical line/message ID/span/observation ID. Compute incremental JSON
byte sizes including fixed schema/seed/chat/organisation context, delimiters and
partition identifiers, and retain the final existing `_call` size check. Cap is
100,000 bytes even if a larger value is requested; smaller injected limits work.
Oversized indivisible observations or fixed context fail before any entity call.

For this conservative first fix, every target batch reviews every evidence
partition. No speculative relevance filtering discards cross-chat/indirect facts.
`partitions`, `required_batches` and `completed_batches` retain the complete planned
target/evidence coverage. Scope citations to the current partition. Missing rows,
bad references, timeouts and failed partitions block all affected targets.

Each target receives either a supported schema-valid proposal, `{}` for reviewed
no contribution (empty citations required), or null for unresolved inference.
Only all-complete coverage permits finalization. No-contribution everywhere still
leaves a required target pending. Null never becomes empty success. Accepted
proposals and their partition IDs remain local, including conflicting proposals.

Merge agreeing scalar fields; union compatible `looks_after` and organisation
links deterministically; reject different roles for the same organisation. Preserve
seed circles and existing entity/reference validation. Conflicting scalar fields
or chat targets remain pending with explicit conflict IDs; no last-response-wins,
majority voting, automatic conflict-review model call or unbounded merge request.
Final merged records pass schema validation; Stage G's existing complete-output
validation and atomic export remain unchanged.

Preplanned packet IDs form stable base jobs. The caller's configured allowance is
not increased automatically. Existing Client reservations, retry lineage, three
transmissions/job, shared 20% recovery and deadlines remain enforced. The probe's
existing explicit 10,000-call mock plan accommodates these additional jobs.

### Actual commands and results

Environment: Windows-11-10.0.26200-SP0, CPython 3.12.9, MSC v.1942 AMD64.
Working directory remains the project root recorded earlier. All tests offline.

| Exact command | Tests / outcome | Runtime | Exit |
|---|---|---:|---:|
| `python -B -m unittest discover -s tests -p test_entity_partitions.py -v` before code | 7: 2 passed, 4 failures, 1 error | 0.023s | 1 |
| same, initial implementation | 7 passed | 0.717s | 0 |
| `python -B -m unittest discover -s tests -p 'test_reasoning*.py' -v` | 28 passed | 0.073s | 0 |
| `python -B -m unittest discover -s tests -p test_solution.py -v` | 9 passed | 0.354s | 0 |
| entity partition command, expanded coverage | 12 passed | 1.117s | 0 |
| `python -B -m unittest discover -s tests -v` intermediate | 243 passed | 15.567s | 0 |
| entity partition command, final | 13 passed | 1.214s | 0 |
| `python -B -m unittest discover -s tests -v` final | 244 passed | 13.229s | 0 |

Final suites: zero failures/errors/skips/hangs. Tests include deterministic reversed
observation/reply order; dated/undated ordering; original independent IDs, exact
long-message spans and window provenance; cross-chat/organisation links and seeds;
conflicts; missing/foreign/pending partition decisions; oversized units; real Client
budget/deadline/retry limits; and actual pipeline output preservation after a
successful first entity partition followed by a failed second partition. Existing
worker termination and atomic-output regression tests also pass in the full suite.

`python -B -S tests/offline_readiness.py` ran twice, both exit 0. Each run passed
all six production imports without site packages and Python 3.9 grammar checks.
Fixtures remain 15,000 messages, 60 chats, one person, 3,000 messages in a large
chat, a 15,000-character message and 4,343,866 input bytes. Both stages/pipelines
completed and published validated output; assertions check every target reviews
every original observation ID, local registry equality and complete partitions.

| Run / fixture | Seconds | Peak traced Python bytes | Total fake calls | Entity packets | Largest entity packet |
|---|---:|---:|---:|---:|---:|
| First / sparse | 7.540 | 34,595,526 | 599 | 2 | 11,770 bytes |
| First / dense | 66.434 | 71,394,950 | 765 | 168 | 99,961 bytes |
| Final / sparse | 7.053 | 34,595,800 | 599 | 2 | 11,770 bytes |
| Final / dense | 55.022 | 71,399,529 | 765 | 168 | 99,961 bytes |

Organisation/goal packet counts are one each per fixture (781/2,035 bytes).
The final run added per-target coverage and identical-output assertions. Both
outputs hash to `5e705c870d5660db8ebd88115c26a83707840ce3c062f1a6137f4535a06527b1`.
Final full-suite execution overlapped part of the final dense measurement; timings
are observations under local instrumentation/load, not isolated benchmarks.

The bound refers to `_encoded(entity_packet)`, the existing configured context
packet limit. The full HTTP JSON envelope escapes that content again and includes
system text/model/settings: measured largest request was 14,398 bytes sparse and
112,560 bytes dense. This distinction is intentional and reported, not a claim
that total HTTP payload is below 100 KB. Stage D estimates/reserves against the
entire HTTP request. Memory is tracemalloc peak, not process/child RSS, and fixture
creation is excluded from timing. Fake clocks govern application deadlines;
perf_counter measures real elapsed time independently. No provider latency exists.

### Remaining limitations and stop

Conservative broadcast coverage increases calls with evidence volume and target
batch count. Cached requests, registry and proposals remain proportional to work;
this is bounded per packet, not constant total memory. Fixed context or a single
oversized observation still fails explicitly. Unresolved conflicts remain incomplete
without an automatic semantic review. Organisation/goal/help global caps are
unchanged. Passing mocks does not establish semantic recall or real model accuracy.

Existing modules other than reasoning retain their previously recorded SHA-256s.
No answer files, checker, challenge inputs, real network/model calls, installations
or downloads occurred. Linux launcher/process-group and actual Python 3.9 runtime
remain unverified. No runtime guarantee, production readiness or overall H1 pass
is claimed. Stop for user review; no H2, live pilot or challenge execution.

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


**2026-11-06 pointer (later evidence, appended without altering the original
record above):** the exact next action above has now been executed. A full
ten-scenario Linux acceptance rerun PASSed on Ubuntu 26.04.1 / CPython 3.9.25,
including `launcher_hang` (exit 137, 13.09 s) with the minimal `run.sh`
supervision change, with zero run-owned leftovers and unchanged output hashes;
report: `ai-logs/opencode/session-02-linux-acceptance.json`, consolidation:
`ai-logs/opencode/session-02-h1-final-report.md`. Gate: 4 PASS, 6/7/8/9
approval-dependent. The six probed production hashes above are unchanged
(reasoning.py last changed in the approved Session 11 stage; current value
matches its post-change probe).
