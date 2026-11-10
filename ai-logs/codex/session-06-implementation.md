# Session 06 - Stage D client and budget

Completed 5 November 2026 at the Stage D implementation scope; ready for user
review. Stage E has not started. This is Windows verification, not Linux,
production, live-endpoint, or full-run readiness.

## Files

| File | Change and reason |
|---|---|
| `llm.py` | Replaced the original minimal client with structured failures, process isolation, deadline checks, central reservations/recovery accounting and run-local cache. Resume preserved this design and fixed seven demonstrated acceptance gaps. |
| `tests/test_llm.py` | Added 56 synthetic tests, including actual spawned-child termination and seven resume regressions. |
| `tests/test_no_answer_boundary.py` | Earlier in this session, adapted the mock to the injected transport, added a complete finish indicator, preloaded client stdlib dependencies, and compared in-memory usage. Removed permission to write usage logs; preserved all read/scan/network/evaluator guards and negative controls. No further changes during resume. |
| `ai-logs/codex/session-06-implementation.md` | This report. |
| `ai-logs/codex/session-06-transcript.md` | Abbreviated factual conversation/activity record. |
| `ai-logs/codex/progress-checkpoint.md` | Append-only milestones and final Stage D status. |

No changes to `data.py`, `validation.py`, `solution.py`, `schema.json`, `run.sh`,
approved plans, Stage A/C tests or earlier session reports/transcripts. The project
directory is not a Git checkout; no Git-based preservation claim is made.

## Client and recovery

The exact public signature remains
`chat(messages, model=None, temperature=0, max_tokens=None, response_format=None, timeout=120)`.
Success returns text; failure raises `LLMError` with a safe `detail` dictionary:
code, actionable message, retryability, split recommendation and HTTP status when
available. `Client.request()` additionally accepts an original job ID, cache
context and caller validation function for future stages.

Configuration comes from `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. Requests use
only the configured base plus `/chat/completions`. There is no endpoint/model
fallback, automatic capability correction, external retrieval or redirect.
Environment proxies are disabled. Authentication, permanent HTTP/configuration
errors and certificate-verification failures do not retry. Secrets, payloads,
responses and provider exception bodies are not printed or written to logs.
Usage is now in memory, not `usage.jsonl`.

Responses require one choice, a complete `stop` finish and nonempty text; missing
fields, refusal/content filtering, tool calls and incomplete results fail.
Malformed JSON, duplicate keys and nonfinite constants fail. Requested JSON
object content is parsed and checked. Truncation discards content and sets
`split_recommended`; no splitting, semantic repair or task extraction exists.
Caller validation rejects incomplete stage results before caching. Generic
`json_schema` requests preserve wire compatibility but need the caller's contract
validator for schema assurance; without one, parsed results are never cached.

Timeouts, transport failures, 408/429 and 5xx may retry. Every original job has at
most three transmissions; future repair/split children must reuse its `job_id`.
All extra transmissions share `floor(planned_base_calls / 5)`. A declared plan
also caps original jobs. Without a declared plan, automatic recovery is disabled
rather than inventing a recovery allocation. Exponential waits start at one and
two seconds; numeric Retry-After can raise a wait up to eight seconds. Longer,
invalid or HTTP-date delays stop recovery explicitly instead of retrying early.
Recovery and deadline allowances are rechecked before dispatch.

## Budget, usage and cache

One shared `Budget` reserves full serialized request estimates plus completion
allowances under a lock before dispatch. It checks token capacity, original-job
and shared recovery allowances atomically. Serial `Client` dispatch is the
default; a shared Budget also prevents concurrent clients reserving the same
remaining balance. It rejects nonpositive reservations and rechecks the latest
calibration while locked.

`Budget(token_ceiling=..., planned_base_calls=...)` supports explicit run settings.
The compatibility wrapper also reads optional `LLM_TOKEN_CEILING` and
`LLM_PLANNED_BASE_CALLS`. An absent token ceiling is explicitly unenforced; no
spending limit or price is guessed. When max_tokens is omitted, a configurable
1024-token completion allowance is both reserved and sent. This is an engineering
request default, not a claimed provider output/context limit.

Local inspection found tokenizers 0.23.1, but no configured model-specific
tokenizer asset; tiktoken/transformers were absent. The labelled fallback is full
wire UTF-8 byte length plus 32 framing units, multiplied by a calibrated safety
factor. Reported undercounts increase that factor with 10% headroom; it never
decreases. This is an estimate, not a guaranteed bound for an unknown tokenizer.

Per-attempt records preserve estimated/reserved tokens, reported prompt,
completion and total usage, supported cached/audio/reasoning/prediction detail
categories, attempts, recoveries, automatic retries, waits, elapsed time and
outstanding/unknown reservations. Missing or invalid usage fields remain None,
with their conservative reservation retained, including timeouts and failures.
Known detail counts provide lower bounds even when containing totals are missing;
detail subsets are not added twice to totals. Dollar cost remains unknown.
Provider-reported usage above the ceiling is retained and stops further dispatch;
an unknown estimator cannot retroactively prevent an actual provider overage.

The in-memory cache holds complete client-validated successes only, and caller
validation runs again on hits. Keys hash exact serialized content, endpoint,
model, generation settings, timeout, client version and supplied run/request
context. Context supports stage/schema/prompt/model versions, input/state
fingerprints, timezone policy and as_of. Changes miss the cache; credential
rotation clears it without putting a key in cache keys. An undetectable server
alias remap cannot be anticipated: callers should supply a known model version.
Model/system-fingerprint metadata is retained for successful responses. No disk
cache, database or new runtime module was added.

## Deadlines and workers

`Deadline` uses monotonic time: network cutoff 1620 seconds, local exit target
1770, overall limit 1800. The default wrapper starts from module import; the
future orchestrator must inject its actual run start/shared Deadline. Client
checks precede dispatch, follow preparation, and reject late responses/cache
access. Backoff cannot consume the cutoff. Validation/output time remains after
network work. `check(finalizing=True)` provides the exit-target gate; it is not
a parent-process watchdog or an already-integrated Stage G exit mechanism.

Production HTTP runs in one spawn-based daemon child per attempt. Setup counts
toward the absolute attempt deadline; the child also checks that deadline before
opening HTTP. Responses have a configurable 2 MiB byte limit and bounded shared
memory. Parent reads only after child exit, so a partial IPC write cannot trap it
in a pipe receive or queue feeder shutdown. Timeout cleanup terminates, joins for
0.2 seconds, escalates to kill if needed, then joins for another 0.2 seconds.
Handles close after reaping. Cleanup failure is fatal and prevents another client
dispatch. PID, timing, termination and reap events contain no request content.

Real Windows tests cover success, crash, no result, a hang and a stalled partial
shared-memory write. They assert reaping, nonzero terminated-child exit, bounded
elapsed time, and no additional active children. Kill escalation uses a synthetic
process because Windows termination cannot be ignored as POSIX SIGTERM can.
Actual ignored-SIGTERM/process-group/hung-parent tests remain Linux H1 work.
OS process creation/kernel failure and a hung parent are outside this Python
watchdog's guarantees. `run.sh` is unchanged; the future Linux launcher hard
timeout is still mandatory. No 29:30/30-minute whole-process guarantee is claimed.

## Exact verification

Working directory: `C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert\xpert-cold-start-starter\cold-start`.
Platform: Windows 11, CPython 3.12.9, 64-bit. Times are unittest-reported seconds.

| Run | Exact command | Tests | Seconds | Result / exit |
|---|---|---:|---:|---|
| Initial implementation | `python -B -m unittest discover -s tests -p test_llm.py -v` | 49 | 2.721 | OK / 0 |
| Initial boundary adaptation | `python -B -m unittest discover -s tests -p test_no_answer_boundary.py -v` | 6 | 7.334 | OK / 0 |
| Independent resume baseline | `python -B -m unittest discover -s tests -p test_llm.py -v` | 49 | 3.002 | OK / 0 |
| Independent resume boundary | `python -B -m unittest discover -s tests -p test_no_answer_boundary.py -v` | 6 | 10.729 | OK / 0 |
| Regressions before fixes | `python -B -m unittest discover -s tests -p test_llm.py -v -k regression` | 7 | 0.032 | FAILED, 10 failures including subcases / 1 |
| After fixes | `python -B -m unittest discover -s tests -p test_llm.py -v` | 56 | 2.578 | OK / 0 |
| **Final complete suite** | **`python -B -m unittest discover -s tests -v`** | **167** | **9.999** | **167 passed, 0 failures/errors/skips / 0** |

The seven regressions demonstrated preparation crossing cutoff, unsupported
Retry-After, partial detail usage undercharging, invalid reservations, stale
calibration, expired-worker dispatch and certificate misclassification. All now
pass. Complete suite includes 44 Stage A, 6 Stage B, 61 Stage C and 56 Stage D
tests. Python 3.9 grammar checks pass for the client and its tests; actual Python
3.9 execution, cross-process clock behavior on that interpreter and Linux
packaging/signals/launcher behavior remain unverified.

No live API call, paid experiment, answer-key access, evaluator import/execution,
full-dataset run, package installation or dependency download occurred. Stage B's
synthetic evaluator attempts are blocked before import. Remaining work is future
stage integration, stage-specific validation, provider/tokenizer/pricing/quota
verification and required Linux readiness evidence. **Stop for user review;
Stage E requires explicit approval.**
