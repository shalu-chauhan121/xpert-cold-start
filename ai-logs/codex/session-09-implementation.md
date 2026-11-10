# Session 09 - Stage G production integration

Stage G implementation and local synthetic integration are ready for review.
This is not Linux/runtime readiness, benchmarking or authorization for model spend.

## Files

- solution.py: production A-F pipeline, category gates, shared client/budget and
  run-start deadline, five-array assembly, help stage, final validation and
  deadline-gated atomic export. main retains its two positional arguments;
  keyword injection enables offline end-to-end tests and an in-memory summary.
- reasoning.py: added resolve_help for assist/remind/leave decisions with exact
  open-task coverage, cited task evidence and full Stage C semantic validation.
  Existing extraction/resolution/task-review functions remain unchanged.
- run.sh: plan section 9a timeout wrapper, same two-argument interface. Requires
  timeout utility; sends TERM at 1770s and KILL after 2s. Missing utility fails.
- tests/test_solution.py: nine integration tests using actual production main,
  Stage E/F code, Client with fake HTTP transport and real validation/export.
- tests/test_validation.py: replaced obsolete unimplemented-inference CLI
  assertion with missing-configuration failure and explicitly stripped LLM env
  vars from that subprocess. Retained nonzero status and output-preservation
  assertions. No validation rule weakened.
- tests/test_no_answer_boundary.py: test-only assembly replacement now accepts
  main's keyword context. All boundary guards and negative controls retained.
- Created this report and abbreviated session-09-transcript.md; appended checkpoint.

No edits to data.py, llm.py, tasks.py, validation.py, schema.json, approved plans,
or previous stage reports/transcripts. Compatibility changes were explained
before editing. Architecture remains the six approved Python runtime modules.

## Behavior

main starts monotonic timing before loading, requires complete input, and invokes
assembly. Assembly builds/validates Stage A windows, calls extraction, canonical
organisation resolution, people/chat resolution, goal ranking, then the task
ledger through reasoning.review_task_packet. Each prerequisite must report
succeeded/succeeded_empty. Pending/malformed/timeout/budget/conflicting-task
results block publication; completed empty input is treated distinctly.
Seed-only unsupported entity/goal input fails explicitly rather than becoming
an apparently successful empty result. Required coverage and references are
checked again by Stage C before export.

The same Client/Budget/Deadline is reused throughout the run. Optional
LLM_TOKEN_CEILING and LLM_PLANNED_BASE_CALLS configure existing reservations and
recovery allowance; absent plan means recovery disabled, absent token ceiling
means no invented ceiling. Client configuration uses the supplied endpoint/key/
model. No fallback service exists. Stage results, task provenance and usage remain
in the optional in-memory summary, not in the five-array output or routine logs.
The summary can contain private evidence; callers must not indiscriminately log it.

Output is exactly people, organisations, chats, goals and open_loops. Task IDs,
events, ranks, provenance and flags stay internal. Closed loops retain source,
origin chat and closure evidence without help. Every open loop requires a model
help disposition. UTC is the existing explicit default policy, not an inferred
dataset fact. Reminder timestamps must be after input as_of with explicit offset;
ambiguous dates cannot be silently converted to valid reminders. Missing help,
invalid references, partial batches or invalid reminder timestamps block output.

Export retains exclusive temporary creation, validation, fsync, reread,
revalidation and atomic replacement. It adds exit-target checks before work and
immediately before replacement; expired publication removes its owned temporary
and preserves prior output. Existing export-fault tests remain passing.

## Deadline scope

Network cutoff: 1620s through the shared Stage D client, including worker cleanup.
Local target: 1770s checked after stages and before publication. Linux launcher's
1770s TERM plus 2s KILL schedule is below the 1800s overall limit. No detached
process is introduced. run.sh has LF line endings (verified zero CRLF).

IMPORTANT: Linux timeout availability/semantics, signal delivery, process-group
cleanup and hung-parent/serialization scenarios were NOT executed here. The
wrapper is implemented, not certified. Direct Python invocation has cooperative
parent checks and bounded HTTP workers but no outer hard-timeout supervisor;
run.sh is the intended supervised Linux entry point. Windows tests cannot prove
that production finishes within 30 minutes. Required Linux section 9a evidence
remains outstanding; no submission/runtime readiness claim is made.

## Exact verification

Working directory: C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert\xpert-cold-start-starter\cold-start.
Local environment remains Windows 11 / CPython 3.12.9, 64-bit.

| Exact command | Tests | Runtime | Result |
|---|---:|---:|---|
| python -B -m unittest discover -s tests -p test_solution.py -v | 7 | 0.342s | OK, exit 0 |
| python -B -m unittest discover -s tests -v | 229 | 13.619s | OK, exit 0 |
| python -B -m unittest discover -s tests -p test_solution.py -v | 7 | 0.285s | OK, exit 0 |
| python -B -m unittest discover -s tests -p test_solution.py -v | 9 | 0.287s | OK, exit 0 |
| python -B -m unittest discover -s tests -v | 231 | 13.107s | OK, exit 0 |

Final: 231 passed, zero failures/errors/skips. No hanging test. All 222 previous
tests pass with the two documented harness adaptations. Nine added tests cover
all five nonempty categories, all help actions, closed loops, every stage failure,
model timeout/unknown usage, invalid reminders, cutoff dispatch, exit-time
publication refusal, source/output preservation, deterministic replay and decoys.
The actual main entry point runs under builtins.open/io.open allowlists,
listdir/scandir prohibitions and blocked DNS/socket calls. Same inputs with/without
synthetic answer decoys yield identical requests/final bytes; changed fake help
responses change final output. Existing stronger Stage B audit negative controls
also pass. No claim of OS-wide file/network tracing beyond these test guards.
Python 3.9 grammar checks pass; actual Python 3.9 runtime remains unverified.

## Remaining limitations

Live semantic accuracy, provider compatibility, token/cost/runtime forecasts,
large-volume context sizing, Linux offline packaging and hard-timeout behavior
remain unverified. Existing bounded packet sizes can report incomplete on larger
inputs; no dataset scaling was attempted. A prompt is not proof of entailment or
permission appropriateness. No submission benchmarking, real API calls, paid
experiments, challenge-data inspection, answer access, checker execution,
package installs or downloads occurred. Synthetic decoys are not answer keys.

Stop after Stage G for user review and explicit approval of any further work.
