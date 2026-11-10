# Session 13: consolidated no-spend H1 readiness record

Date: 2026-11-05. **H1 is NOT complete.** Section 11a gates 4, 6, 7, 8 and 9
remain BLOCKED. No live pilot, H2 or full-dataset execution was performed.
No production change was needed or made. No challenge input, answer/checker
file, credential value or real model endpoint was accessed in this work.

## Established evidence reused

The user confirms Ubuntu 26.04 / WSL 2 with CPython 3.9.25, 244 passing unit
tests (64.844 seconds in Session 12), all six boundary tests, successful sparse
and dense 15,000-message fixtures, and six unchanged production hashes. These
are established results; they were not repeated or recast as agent-run Linux tests.

Sessions 10-12 were reviewed with AGENTS.md, the approved plan Sections 9a,
11/11a, and the latest checkpoint. Earlier historical statements that Linux
was unavailable are superseded by the user's installation/validation evidence.
**Access from this agent is a separate limitation:** the current WSL command
failed with `WSL/Service/E_ACCESSDENIED`. No elevation, installation, download
or alternative Linux environment was attempted.

Session 11's existing local scale observations remain useful: sparse 4.244s,
34,595,776 traced bytes, 599 fake calls; dense 30.725s, 71,398,973 traced bytes,
765 fake calls, 168 entity packets and largest entity context 99,961 bytes.
Those timings/memory measurements are Windows results, not newly measured
Ubuntu metrics or a live-runtime forecast. Both fixtures include a large chat
and long messages. The successful Ubuntu reruns are separately established.

## Files changed

| File | Change |
|---|---|
| `tests/test_solution.py` | Added one deterministic display-name renaming/replay regression using the existing guarded synthetic pipeline |
| `tests/linux_acceptance.py` | New standalone Linux 3.9.25 acceptance harness; does not join ordinary unittest discovery |
| `ai-logs/codex/session-13-h1-readiness.md` | This consolidated report, estimate method and pilot proposal |
| `ai-logs/codex/session-13-linux-acceptance.json` | Actual BLOCKED preflight result from this Windows environment |
| `ai-logs/codex/session-13-unit-tests.txt` | Actual full-suite output, interpreter and exit status |
| `ai-logs/codex/session-13-export.py` | Original-log exporter, scoped to this actual task prompt |
| `ai-logs/codex/session-13-transcript.md` | Chronological actual user/assistant/tool records, with credential redaction |
| `ai-logs/codex/session-10-implementation.md` | Appended pointer/status for the existing H1 report |
| `ai-logs/codex/progress-checkpoint.md` | Appended current readiness and blockers |

Historical report bytes and transcripts are preserved. The original session
JSONL is accessible; export begins at the actual Session 13 task prompt.
The transcript retains source line numbers, timestamps, payloads and a snapshot
hash, excluding internal reasoning/configuration and duplicate UI messages.
Its header states the captured endpoint and whether the final reply is present.
An exporter watcher is used for final-response capture; missing records are
never reconstructed. There is no Git repository here, so a Git diff is unavailable.

## Actual commands and results

Commands below ran from the project unless otherwise noted. No already-passing
volume test or Linux full suite was repeated.

| Command/check | Actual result |
|---|---|
| `wsl -d Ubuntu --exec /bin/sh -c 'command -v python3.9; python3.9 --version; uname -s'` | Exit 1, `WSL/Service/E_ACCESSDENIED`; no Linux command ran |
| `python -B -m unittest discover -s tests -p test_solution.py -v` | Windows Python 3.12.9: 10 tests passed, 0.436s |
| `python -B -S tests/linux_acceptance.py --report ai-logs/codex/session-13-linux-acceptance.json` | BLOCKED, script exit 2: requires Linux CPython 3.9.25; no acceptance scenario ran |
| `ast.parse(..., feature_version=(3,9))` on the new harness | Passed; syntax check only, not Linux execution |
| `python -B -m unittest discover -s tests -v` | Windows Python 3.12.9: 245 passed, 12.829s, exit 0; full output saved |
| SHA-256 comparison for data/llm/reasoning/tasks/validation/solution | All six match the original recorded hashes |

The new display-name regression checks that renamed chat/sender metadata reaches
the request, while stable IDs, fixed semantic replies and final output remain
consistent; a repeated renamed run has identical requests and bytes. It tests
mechanics, not the live model's semantic invariance to names.

## Section 9a Linux acceptance

**All fresh scenario measurements are BLOCKED by agent-to-WSL access.** No
elapsed time, exit code, PID, group cleanup or reap success is claimed for a
Linux scenario that did not execute. Existing Windows tests are supporting
evidence only. The new harness is prepared and syntax-checked but unvalidated
on Linux; execution may expose a harness issue or production blocker.

| Required scenario | Existing evidence / prepared acceptance | Current Linux status |
|---|---|---|
| Worker hangs before response | Existing spawned hang test; harness drives real ProcessTransport through solution.main, checks incomplete state, bounded terminate/reap and unchanged output hash | BLOCKED |
| Slow partial response | Harness loopback HTTP trickles bytes through the real HTTP worker; records byte-progress timestamps and total deadline outcome | BLOCKED |
| Stalled transfer | Loopback server sends a partial body then stalls; checks bounded worker outcome and preserved output | BLOCKED |
| Retry delay exceeds network cutoff | Existing fake-clock cutoff tests; harness real monotonic 6s cutoff receives Retry-After 7s, requires one dispatch, no sleep/retry and incomplete output | BLOCKED |
| Worker crash or invalid result | Existing spawned crash/empty tests; harness crash exit 7 and corrupt IPC result, explicit failure and reaped PID | BLOCKED |
| TERM ignored, force-kill required | Existing synthetic-process escalation test is insufficient; new real worker installs SIG_IGN, requires kill event and exit -SIGKILL | BLOCKED |
| Hung main, outer launcher | Test-only copy of run.sh changes only 1770/2s to 12/1s; injected hung main and non-detached TERM-ignoring child; requires exit 137 and no surviving/zombie group members | BLOCKED |
| Normal successful launcher | Unmodified production run.sh, pinned existing Python 3.9.25, synthetic truly empty input; requires exit 0 and valid five-array output | BLOCKED |
| Interruption during temp write | Actual production export with test-only slow json.dump after partial flush; shortened launcher TERM; requires exit 124, injection marker and unchanged final hash | BLOCKED |

The harness records distribution, interpreter, timeout version, spawn method,
commands, real monotonic elapsed times, dispatch/cutoff/terminate/kill/reap
events, worker exit codes, marker PIDs/PGIDs, response progress, stage outcome,
and before/after hashes. It polls `/proc` for surviving group members including
zombies. It never treats emergency cleanup as a successful acceptance result.
An uncatchable interruption may leave an unpublished temporary, consistent with
the existing export contract; the final output must remain unchanged.

Acceptance bounds are fixed in advance: worker attempt 3s, worker grace 0.2s
per terminate/kill join, scheduling tolerance 2s; application network/exit
settings 6/10s; outer TERM 12s, KILL grace 1s, outer cleanup bound strictly
below 15s; independent subprocess emergency timeout 20s. Normal launcher
success must finish before the harness emergency limit. No bound is widened
automatically on failure. Failure records are not proof of process cleanup;
inspect them and remaining processes before accepting any rerun.

Production constants are checked separately: network 1620s, application and
launcher target 1770s, launcher kill grace 2s, overall allowance 1800s. This
leaves 150s from network cutoff to finalization target and 28s after nominal
force-kill for startup/cleanup scheduling; those margins are budgets, not
measured worst-case guarantees. Accelerated tests do not establish live latency.

## Offline packaging

Established Ubuntu full-suite/volume evidence supports the existing stdlib-only
six-module deployment and single scoped schema validator. No package install is
needed for those paths. The new harness additionally requires an already
installed `bash`, GNU-compatible `timeout`, `/proc`, and exact CPython 3.9.25.
It runs with `-S`, imports the six modules, constructs the selected validator,
and validates real export through the unmodified launcher. The launcher's
python3 is pinned by an owned test wrapper to the current interpreter, using
`-B -S`; production run.sh is not changed. External socket connections and DNS
are audit-denied; only the owned loopback HTTP fixture is permitted. This is
not a claim of an OS-wide network namespace firewall.

Fresh packaging/launcher verification remains BLOCKED until that command runs
on Ubuntu. Do not download missing prerequisites; report them as blockers.

## A-G synthetic evidence audit

The established Ubuntu 244-test result and current Windows 245-test result are
used together. Only the new display-name case lacks a Linux execution result.

| Stage / requirement | Existing concrete evidence |
|---|---|
| A: raw IDs/text, mixed scripts, stable chronology, invalid structure, exact primary coverage | `test_data.py`: original records, chronology, conflicting IDs, missing/unknown references, media, zero-message chats, long Unicode spans, full-character matrix, primary/context overlap ordering and coverage failures |
| B: read boundary and decoy independence | `test_no_answer_boundary.py`: six tests, both open-event layers authorized; forbidden builtin/io/path/os opens, scans, cached/direct checker imports, unchanged nonempty requests/results with decoys; solution guarded real-entry probe |
| C: schema, evidence and atomic export | `test_validation.py`: schema rules and unsupported keywords, both/neither targets, extra fields, >10 goals, ownership/references, closure/help/date constraints, no backend fallback, no-site subprocess, interrupted write/flush/fsync/replace and old-output preservation |
| D: response failures, caps, waits, usage, cache and secrecy | `test_llm.py`: malformed/empty/truncated/refused responses, transient/auth failures, per-job/shared recovery caps, reservations, unknown usage, cache context invalidation, cutoff/overshoot, privacy diagnostics and real spawned workers; POSIX extensions remain gate 4 |
| E: shared extraction, categories and ranking | `test_reasoning.py`: provenance/overlap, partial acknowledgement, unknown evidence, completed-empty versus timeout. `test_reasoning_resolution.py`: alias/shared participant distinction, group-to-person, seed/multiple chats, missing batches, >10 exact top goals, fewer without padding, adoption, duplicates/forwarded evidence, tiers/timezone/ties and permutations. `test_entity_partitions.py`: complete broadcast coverage, bounded packets, conflicts/pending, no contribution, cross-chat consistency, preserved seed/link values |
| F: ledger semantics after accepted decisions | `test_tasks.py`: acknowledgement, negated cancellation, completion/reopen, new deliverable, owner reassignment, two tasks/message, overlap provenance, cross-chat closure, unrelated similar task, ambiguous review, exhaustive candidate partitions, late/permuted replay and conflicting simultaneous events |
| G: help and full integration | `test_solution.py`: nonempty all-five-category output and assist/remind/leave, needs_yes, closed tasks without help, invalid reminder, each stage failure, cutoff before publication, deterministic repeated output and new display-name renaming. Validation tests cover due-date ambiguity/required values |

Section 4b evidence: people/chats cannot pass pending target batches; empty
input and zero-message chats are distinguished; goal rejection/no candidates
differs from pending/failed classification; closed tasks remain in output and
help becomes succeeded_empty; extraction failures and unprocessed events do
not become empty success. Task `ambiguous_evidence` is explicitly distinct
from incomplete candidate search. Existing integration failures preserve old
output at every stage. These are mechanics checks on accepted fake semantics,
not evidence of live language quality; that is gate 7.

## Section 11a approval checklist

PASS means the stated gate's evidence exists, not permission to spend.

| Gate | Status | Evidence / missing requirement |
|---|---|---|
| 1. All category paths and evidence protections | PASS | A-G evidence above; nonempty five categories, all help actions, seed/provenance/goal/ledger tests; 244 Ubuntu tests plus 245 local tests |
| 2. Failures are not empty success | PASS | Section 4b mapping above, stage-failure/partition failure/atomic export hash checks |
| 3. Answer isolation | PASS | Established six Ubuntu boundary tests, unchanged security checks and guarded integration |
| 4. Offline Linux validation and cleanup | BLOCKED | Established packaging evidence reused; missing real POSIX force-kill, launcher and interrupted-write acceptance measurements; agent WSL access denied |
| 5. Local scale and bookkeeping without spend | PASS | Established successful sparse/dense 15,000-message runs; volume/coverage, request/output size, local time/memory evidence in Sessions 10-12 |
| 6. Separately approved and reviewed bounded live pilot | BLOCKED | No pilot authorized/executed; proposal below only |
| 7. Critical semantic review | BLOCKED | Requires actual pilot responses and manual raw-message review across languages/patterns |
| 8. Concrete dataset budget/time forecast fits | BLOCKED | No authorized actual input/window metadata, pilot latency/density/usage, verified pricing or enforceable provider spend limit |
| 9. Approval of the specific full run | BLOCKED | No exact approved dataset/model/configuration/output path and maximum full-run spend; H2 prohibited |

No demonstrated production FAIL is claimed from an unavailable Linux run.
Any failed acceptance scenario or pilot semantic defect must change the
corresponding gate to FAIL, with evidence and a specific remediation proposal.

## Input-only time/cost estimation method (prepared, not executed)

1. After separate input-only authorization, use exactly the three named inputs
   with existing `load_input` and `build_windows` (4000 primary characters,
   32 primary spans, two preceding context spans). Never enumerate for data,
   inspect labels or invoke the checker. Record source/configuration hashes,
   chat/person/message counts, long-message spans, exact window count W and
   full serialized request byte distributions. User-supplied aggregate metadata
   can support a provisional range, but cannot prove exact windows/coverage.
2. Base extraction calls = W. Use pilot low/high observation densities per
   window and worst observed encoded observation sizes to forecast organisation,
   entity, goal, task and help packets. Count entity calls over evidence
   partitions AND target batches (default target batch 32); broadcast means
   counting people/chats once understates work. Organisation/goal/help packet
   overflows are explicit failures under existing caps, not an assumed unlimited
   splitting mechanism. Reject forecasts that require unsupported splitting.
3. Task interpretation calls track candidate task observations; same-chat and
   explicit cross-chat matching add the sum of candidate batches per event
   (default 16 candidates), including exhaustive later partitions. Include
   closed/reopened/reassigned tasks and unmatched/ambiguous events. Help applies
   to every final open task, not all discovered tasks. Count all five categories.
4. Let B be total base calls across the actual request families. Reserve global
   recoveries R = floor(B/5), while retaining each original job's maximum three
   transmissions, including repairs/split children. Planning total <= B + R;
   do not mistake planned_base_calls for an enforced total-call cap. Cache hits
   count as zero only for proven identical complete requests; cold planning
   assumes no cache savings. Budget up to 8s backoff per recovery as a bound,
   plus the corresponding repeated inputs and completion allowance.
5. Completion reservations use actual configured maxima: 2048 for extraction
   and task review, 4096 for organisation/entity/goal/help. Account for the whole
   wire envelope, schemas, metadata and escaped context in input estimates.
   Apply the existing upward usage calibration and retain unknown usage as
   reserved/possibly billed. UTF-8 byte estimates are a proxy, not a guaranteed
   tokenizer bound. Do not double-count cached/reasoning tokens already included
   in provider totals; price them only according to verified billing rules.
6. Prepare low/high call and token tables per family. Conservative sequential
   network time = sum(high family calls * slowest representative family latency)
   + high retries * slowest retry latency + 8R seconds. Add local preprocessing,
   response validation and packet construction on the same critical path, then
   an explicit proposed 25% safety allowance. Test this upper forecast against
   1620s; averages alone do not justify scaling. Few pilot observations are not
   a reliable tail-latency bound and may require a separately approved extension.
7. Reserve the full 150s post-network window through 1770s for final validation,
   serialization, fsync, atomic publication and cleanup. Preserve the 2s outer
   escalation and remaining 28s startup/scheduling margin before 1800s; verify
   those mechanics via Section 9a. Do not use finalization time for model work.
8. With approved model/endpoint identity and verified per-category prices,
   calculate upper cost from reserved input/output and retry tokens, counting
   timed-out unknown work as potentially charged. Compare with a hard approved
   spend ceiling and provider controls. Without those facts, report cost UNKNOWN,
   never a made-up price or zero cost for missing usage.

Unavailable now: exact dataset paths/counts/windows/seed and message size
distributions; downstream semantic density and cross-chat candidate breadth;
model/provider configuration and pricing; pilot usage/latency/repair frequency;
actual account quotas and enforceable billing controls. No numerical full-run
time, token or money forecast is justified. Input-only access is a separate
authorization from a live pilot or full run.

## Bounded live-pilot proposal -- NOT authorized or executed

Propose a synthetic-only pilot with the intended unchanged production model,
endpoint, prompt versions and schemas, after Linux cleanup acceptance and
separate approval. No challenge messages or reference labels are needed.

| Request variant | Proposed base-call allocation |
|---|---:|
| Shared extraction across declared multilingual fixtures | 5 |
| Organisation reconciliation | 1 |
| People/chat entity resolution | 3 |
| Goal resolution/ranking | 1 |
| Task semantic interpretation | 8 |
| Same-chat / explicit cross-chat task matching | 4 |
| Help decisions spanning assist/remind/leave | 3 |
| Total base / shared recovery allowance / hard total attempts | 25 / 5 / 30 |

These are upper allocations, not a promise of coverage in 25 calls. Every
required family needs a valid observed response. If early stages generate more
work, stop incomplete at the cap; do not bypass validation or silently expand.
Retain three transmissions per original job and the shared five-recovery limit.

Proposed hard spending ceiling: **USD 2.00**, subject to explicit approval and
verified enforceability; this is a spending proposal, NOT an estimated price.
Proposed total token-reservation ceiling: 250,000, with unchanged per-request
completion maxima. Base completion allowances total 67,584; five worst-size
recovery completions add 20,480, for up to 88,064 completion tokens. Input and
output together must fit the reservation ceiling; large packets may stop the
pilot earlier. Proposed pilot network cap 600s, application finalization target
750s and supervisor TERM/KILL bound 780/2s, all within production ceilings.

Before dispatch, an approved test/pilot runner must enforce the independent
30-attempt limit (the current Budget base-call plan does not), elapsed limit,
token reservations and monetary upper bound/provider spend control. It must
refuse dispatch if unknown usage could exceed the remaining USD 2.00. The
production byte estimator alone cannot guarantee dollars. No runner making
real requests was built or invoked here. Exact intended model/endpoint identity,
prices and spend controls remain prerequisites to final pilot approval.

Predeclare synthetic English, Hindi, Bengali and Hinglish cases covering:
acknowledgement without closure; negated cancellation; completion then reopening;
owner reassignment; two distinct obligations; explicit cross-chat completion
versus an unrelated similar task; forwarded promotion versus an adopted user
goal; unsupported goals; all help actions including permission and ambiguous
reminder timing; a group assigned to a person; seed preservation. Review both
returned items and independent input windows to find omissions. Keep reviewer
expectations outside inference prompts. Name-renaming and paraphrase pairs
probe semantic sensitivity without claiming an accuracy threshold.

Record request family and job/attempt IDs, sanitized configuration and code/
prompt hashes, actual start/end latency, input/output/reasoning/cache usage
where exposed, finish/refusal/truncation metadata, retries/repairs, unknown
billing, packet sizes, category coverage, validation and semantic errors.
Manually review supporting original synthetic text and outputs. Fabricated
evidence, false closure, omitted required categories or ignored input blocks
scaling; document other uncertainty. A small pilot is not hidden-set accuracy
evidence and cannot authorize a full run.

## Remaining blockers, approvals and exact next action

1. **Immediate no-spend next action:** run the prepared acceptance harness from
   the already installed Ubuntu environment with project files available:

   ```sh
   cd '/mnt/c/Users/Shalu Chauhan/OneDrive/Documents/Xpert/xpert-cold-start-starter/cold-start'
   python3.9 -B -S tests/linux_acceptance.py --report ai-logs/codex/session-13-linux-acceptance-ubuntu.json
   ```

   This command is proposed, not run. If the Linux checkout is elsewhere, use
   that project directory. The report must say PASS for every case and include
   real evidence. A BLOCKED/FAIL result must be reviewed; do not treat harness
   preparation as Linux acceptance. The agent needs a functioning authorized
   Linux execution channel, or the actual report from this user-run command.
2. After resolving gate 4, seek separate approval for the concrete bounded pilot
   only after intended endpoint/model, pricing and enforceable spend controls
   are supplied. No such approval is requested or presumed by executing this
   no-spend task.
3. Gate 8 additionally requires authorized input-only metadata planning and
   reviewed pilot measurements. Gate 9 then requires an exact full-run proposal
   and explicit spend/scope approval. Stop before live execution and H2.
