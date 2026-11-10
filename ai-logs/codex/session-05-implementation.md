# Session 05 — Stage C validation and export

Date: 4 November 2026. Verdict: **Stage C completed at its approved implementation scope**, with local Windows verification. Linux execution and actual Python 3.9 execution remain unverified; this is not H1 readiness or production inference readiness. Stop for user review; Stage D has not started.

## Scope and files

Read `AGENTS.md`, the Session 02 architecture, revised plan (including sections 1, 8, 11, 11a, 12 and relevant evidence/state rules), checkpoint, actual schema, loader, runner and existing test files. Inspected the starter structure, README and launcher. The architecture file ends at its help-policy section. No evaluator source was read.

| File | Change |
|---|---|
| `validation.py` | Added the single schema backend, strict JSON reader, actionable errors and project semantic checks. |
| `solution.py` | Integrated Stage A loading, explicit incomplete-inference failure, validated atomic export and nonzero failure exit. |
| `tests/test_validation.py` | Added 61 unittest methods with synthetic inputs, schema mutations, reference/date checks, CLI tests, backend isolation and export failure injection. |
| `tests/test_no_answer_boundary.py` | Narrow compatibility update for the validation module, local schema and owned atomic-export temporary; test-only assembly replaces the old production baseline. |
| `ai-logs/codex/session-05-implementation.md` | This report. |
| `ai-logs/codex/session-05-transcript.md` | Accessible session transcript excerpts and actual tool/test record. |
| `ai-logs/codex/progress-checkpoint.md` | Append-only Stage C status. |

`data.py`, `tests/test_data.py`, `schema.json`, `llm.py`, `run.sh`, approved plans and prior session records were not edited. No dependencies, new application framework, reasoning module or task ledger were added.

## Backend decision and offline evidence

Selected **`xpert-scoped-schema` version `1.0.0`**, implemented solely in `validation.py`, with Python 3.9+ standard-library APIs. This follows the explicitly permitted fallback *design decision* in revised-plan section 1; there is no runtime backend fallback.

Before implementation:

- Local interpreter: Windows CPython **3.12.9**. `importlib.util.find_spec` located installed `jsonschema` and `referencing`.
- Local metadata and a successful import verified `jsonschema` **4.26.0**, `Requires-Python >=3.10`, and `Draft202012Validator`. Required dependencies include `attrs`, `jsonschema-specifications`, `referencing`, and `rpds-py >=0.25.0`. That Windows installation is not a portable Python 3.9 Linux supply.
- `python -B -m pip cache list` reported **No locally built wheels cached**. No dependency bundle exists in the inspected starter structure. No package was downloaded or installed.
- `Get-Command python,python3,wsl,docker -ErrorAction SilentlyContinue` found Python and the WSL launcher, but no Docker command. `wsl --list --quiet` reported that WSL is not installed. Consequently no compatible pinned dependency set could be supplied and verified on Linux here. Windows binaries were not copied into a submission.

Chosen target compatibility remains the starter's **Linux/Python 3.9+**, with nothing to install. The selected backend needs only the source and adjacent actual `schema.json`. A fresh `python -B -S -c ...` subprocess test disables site packages, rejects imports of external validators and dependencies, installs an audit guard against DNS/socket connections, proves the guard rejects a synthetic lookup before any lookup occurs, and validates the complete five-category fixture. It passed. An additional subprocess denies the selected `validation` import and confirms an uncaught `ModuleNotFoundError`, with no attempt to import another backend. Missing/corrupt schema and unsupported keywords also fail explicitly.

As a development-only reference, the already installed `jsonschema` 4.26.0 Draft 2020-12 validator agreed on **141** schema checks across **13** schema tests, with DNS/socket access blocked. Production never imports it. The actual schema has no references; the custom backend loads only its local file, never fetches its `$schema` URI, and explicitly rejects `$ref`/`$defs` rather than inventing resolution behavior. This is support for the plan's exact vocabulary, **not a claim of full Draft 2020-12 compliance**.

Both new runtime source files parse with Python 3.9 grammar. This checks syntax, not execution on a Python 3.9 interpreter. Actual Linux/Python 3.9 validation remains a platform verification limitation for later readiness work.

## Rules implemented

`SchemaValidator` reads the actual file rather than copied categories/enums. It validates schema configuration before instances, including unused branches. Supported assertions are exactly `type`, `enum`, `required`, `properties`, boolean `additionalProperties`, object-schema `items`, `minItems`, `maxItems`, and `oneOf`; `$schema`, `title`, and `description` are metadata. Unknown keywords or unsupported schema forms fail with `SchemaError`. The identified dialect is 2020-12. JSON types distinguish booleans from numbers. Nonfinite values, non-JSON containers and non-string object keys are rejected. Decoding rejects duplicate keys and nonfinite constants.

The supplied schema enforces all five required arrays, required nested fields, enum values, primitive/item types, all prohibited extra fields, ten-goal maximum, nonempty goal evidence, and exactly one chat target. Errors identify JSON-pointer paths and reasons; schema errors cannot become successful empty output.

Project checks require:

- Complete Stage A input; failed/incomplete loads cannot be exported.
- Exactly one output record for each input person and chat, including silent participants and zero-message chats; no unknown persons/chats, duplicate record IDs, blank IDs or `ME` person record.
- Existing organisation targets/links, person chat targets and care references. Care may target `ME`; a self-care link is not a care relationship. Owners may be `ME` or represented input people, never organisation/chat IDs or invented people.
- Existing message IDs for every goal citation, loop source and closure; loop source belongs to its declared origin chat.
- Done/dropped loops have existing closure evidence and no non-null help. Open/reopened loops have no current closure and do have a help decision. Closure cannot predate origin; equal timestamps are allowed without inventing an order. Cross-chat closure is allowed.
- Assist requires nonblank `next_step` and boolean `needs_yes`; remind requires nonblank `remind_at`; leave requires nonblank `reason`. Actual schema rules validate the help object's fields and enum.
- Due dates, when present and non-null, are real Gregorian `YYYY-MM-DD` dates. Unknown due dates remain omitted/null. Past due dates do not close a loop.
- Reminder timestamps use explicit `Z` or signed `HH:MM` offsets, calendar date, `T`, hours/minutes/seconds, and optional 1–6 fractional digits. Impossible times and offsets fail. A reminder must be strictly after the input's maximum Unix timestamp (`as_of`), never after an invented wall-clock reference. No implicit Asia/Kolkata assumption or scheduling policy is introduced. Relative-date interpretation remains deferred as in the plan.

Validation never changes supplied output or evidence. Valid known-person ownership need not equal the sender or a source-chat participant. The final schema has no fields for ownership proof or reviewed cross-chat links: this stage checks referential consistency and chronology, not whether arbitrary existing message text entails a goal, assignment or closure. Language interpretation and supported-link review remain Stage E/F responsibilities. This limitation is explicit; a valid ID alone is not claimed as proof of meaning.

## Integration and atomic export

The two CLI arguments are unchanged. `main()` loads through the existing Stage A allowlist, requires complete input, assembles all results, and calls `export_output()`. Invalid input/output, schema failure or write failure returns 1 with a diagnostic; incorrect CLI arity returns 2.

The starter's blanket-friend / one-organisation-per-group baseline is no longer published as completed inference. At Stage C, any nonempty chat/message input or nonempty seed content produces an explicit incomplete error and preserves the destination. Only genuinely empty input can complete without later inference. `assemble_output()` is the narrow integration seam for later stages. Synthetic tests patch only that seam to exercise valid nonempty publication and invalid output rejection through real `main()`. No later-stage processing-state machinery or model orchestration was implemented.

Export sequence: validate the full object in memory; exclusively create a uniquely named `.output-name.<uuid>.tmp` beside the destination; serialize strict UTF-8 JSON; flush, fsync and close; strictly decode and revalidate the file; check it equals the original object; finally call `os.replace`. The final path is never opened for partial writing. All handled failures and `KeyboardInterrupt` run cleanup. An exclusive-create collision preserves the other writer's file. Successful export leaves no temporary.

Tests inject partial serialization, flush, close, fsync, corrupted serialization and replacement failures. Every failure asserts exact old destination bytes and no owned temporary files. Failure without an old destination leaves the final path absent. The replacement hook observes complete schema/semantic-valid serialized JSON while the old destination is still unchanged.

Atomic replacement assumes normal same-filesystem `os.replace` semantics. This does not guarantee directory-entry durability through power loss, or cleanup after uncatchable process termination; a kill may leave an unpublished temporary. No recursive cleanup or process supervisor was introduced.

## Stage A/B compatibility

Stage A code/tests remain unchanged. Stage B's previous guard allowed direct writing of `output.json` and only the three input reads, so it could not allow required schema reads or temporary-file revalidation. Its update preloads the new runtime source, permits exactly the adjacent project schema, and tracks exclusively created destination-specific UUID temporary files for writing and rereading. Rename is restricted to a tracked temporary and the designated output. Output itself remains unreadable under the runtime guard; existing unapproved-read, scan, evaluator and external-call negative controls remain active.

The old naive result producer moved into the test harness because production must fail while inference is unimplemented. Identical permitted inputs with/without synthetic decoys still yield identical actual validated final output and identical mocked wire requests; changing a permitted participant still changes both. All six Stage B tests and their 19 negative-control subcases pass. This is a necessary artifact/assembly compatibility adjustment, not a change to Stage B's permitted dataset boundary. The previously recorded Stage G requirement to test real model orchestration remains outstanding.

## Executed tests

Working directory for every command below: `C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert\xpert-cold-start-starter\cold-start`. Durations are actual unittest-reported seconds, not performance claims. All fixtures were synthetic. Child CLI/backend probes and fault cases are included in their enclosing unittest runs; their individual durations were not separately measured.

| Order | Exact command | Tests | Duration | Result / exit |
|---|---|---:|---:|---|
| 1 | `python -B -m unittest discover -s tests -p test_validation.py -v` | 57 | 1.307s | OK / 0 |
| 2 | `python -B -m unittest discover -s tests -p test_no_answer_boundary.py -v` | 6 | 7.308s | OK / 0 |
| 3 | PowerShell here-string reference script piped to `python -B -` (exact script in transcript) | 13, 141 comparisons | 0.196s | OK / 0 |
| 4 | `python -B -m unittest discover -s tests -p test_validation.py -v` | 61 | 1.436s | OK / 0 |
| 5 | `python -B -m unittest discover -s tests -p test_data.py -v` | 44 | 0.439s | OK / 0 |
| 6 | `python -B -m unittest discover -s tests -v` | **111** | **10.425s** | **OK / 0** |

Runs 4/5 were independent and executed concurrently. The increase from 57 to 61 added selected-backend import failure, main's write-failure status, missing schema preservation and first publication. No tests failed in this session. Post-test inspection found no Stage B/C owned fixture directories remaining; historical Stage A cleanup limitations were not revisited.

## Operational failures and limitations

- Initial required-file reads ran from workspace root, where those paths did not exist (command exit 1). Located the starter project using shallow directory listings, then read the required files there.
- One combined patch attempted delete/add on the same `solution.py` path and was rejected before applying changes. Applied the new module and runner in separate operations. PowerShell's temporary UTF-8 BOM on the rewritten runner was removed before tests.
- `git status --short` returned exit 1 because this directory is not a Git checkout. No Git-based diff/preservation claim is made.
- WSL is not installed; local Windows offline tests and syntax checks do not certify Linux/Python 3.9 execution. No installation or download was attempted.
- Textual evidence entailment, extraction completeness tracking, live inference quality, budgets/deadlines, task state replay and production orchestration remain in later stages. Nonempty CLI incompletion is intentional and tested.

No actual answer files were accessed, inspected, imported, copied or used. No evaluator was read, imported or invoked. Stage B's synthetic evaluator-import attempts are intercepted before import. No real model/API calls, network downloads, paid pilot, full-dataset run, or readiness work occurred. Existing reports/transcripts are preserved; the checkpoint's preceding 11,031 bytes are preserved byte-for-byte. **Stage D has not started and requires explicit user approval.**
