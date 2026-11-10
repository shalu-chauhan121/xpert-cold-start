# Session 04 — Stage B no-answer boundary

Stage B tests are implemented and ready for review. Stage A and all production
modules remain unchanged. Stage C has not started and requires explicit approval.

Added `tests/test_no_answer_boundary.py`: six standard-library unittest tests,
including 19 negative-control subcases. Each probe runs in a fresh interpreter
with a synthetic fixture containing the three permitted files. Decoy answer
JSON files, an extra JSON file, and a synthetic checker are created only inside
the test-owned directory. No real dataset or answer directory is used.

The child preloads standard-library dependencies and compiles exactly the three
existing runtime sources before enabling its guard. It then executes fresh module
bodies under the guard. CPython audit events intercept file opens (including
builtins, io, pathlib, and os.open) and prohibit directory discovery. Only the
three input paths may be read; only the synthetic output and usage paths may be
written, with read/write modes forbidden. Source-code preparation and test
artifact inspection are outside the inference guard and are not input reads.
Import wrappers additionally catch cached checker imports; audit events reject
checker execution. Recorded violations fail the probe even if runtime code
catches their exceptions. Socket connections, DNS, and subprocess launches are
blocked inside the guarded run. The existing HTTP transport is replaced with
a fixed synthetic reply; no real LLM/API request occurs.

The existing baseline does not call the new loader or the model. To avoid
implementing future stages, the tests exercise two explicit paths in the same
guarded probe: Stage A loading/window construction into the existing HTTP client
using a test-only payload, and the unchanged baseline `solution.main()` producing
its actual output file. Exactly one nonempty serialized HTTP request, the fixed
model reply, baseline output bytes, and deterministic usage bytes are compared
across absent/present decoys. Changing a permitted participant changes both the
request and baseline output, ruling out constant-result comparisons. This is
boundary verification of current components, not a claim that the future model
pipeline or production prompts exist.

| Stage B requirement | Test in `NoAnswerBoundaryTests` | Result |
|---|---|---|
| Synthetic three-file environment and decoy answers directory | `test_requests_and_final_outputs_are_identical_with_and_without_decoys` (`setUp` / `add_decoys`) | Pass; identical allowed inputs reused, synthetic decoys added between fresh runs |
| Intercept opens and prohibit scans | `test_guard_rejects_unapproved_opens_even_when_caught`; `test_guard_rejects_directory_discovery_even_when_caught` | Pass; 6 read controls and 8 scan controls rejected before access |
| Read only the three permitted data files | `test_inference_reads_only_allowed_files_without_scans` | Pass; loader reads each once; baseline reads chats/messages; combined read set is exactly the three allowed names |
| No inference import of `check.py` | `test_inference_never_imports_checker_including_initialization` | Pass; clean initialization/run plus 5 rejected checker controls, including cached import and direct execution |
| Fixed mocked responses with/without decoys | `test_requests_and_final_outputs_are_identical_with_and_without_decoys` | Pass; one actual client request intercepted per run and exact fixed reply asserted |
| Identical payloads and final outputs regardless of decoys | `test_requests_and_final_outputs_are_identical_with_and_without_decoys` | Pass; serialized request bodies, reply text, output bytes, and usage bytes identical |
| Positive sensitivity control | `test_allowed_input_change_affects_requests_and_output` | Pass; changed allowed input changes request and baseline output |

All commands below ran from
`C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert\xpert-cold-start-starter\cold-start`
on Windows, Python 3.12.9. Times are unittest's reported durations.

| Exact command | Tests | Duration | Result / exit |
|---|---:|---:|---|
| `python -B -m unittest discover -s tests -p test_no_answer_boundary.py -v` | 6 | 7.998s | OK / 0 |
| `python -B -m unittest discover -s tests -p test_data.py -v` | 44 | 0.677s | OK / 0 |
| `python -B -m unittest discover -s tests -v` | 50 | 8.390s | OK / 0 |

Three earlier runs of the exact Stage B command failed during test development:

| Run | Actual result | Cause and correction |
|---|---|---|
| 1 | 5 tests, 5.459s, FAILED (failures=9), exit 1 | Windows does not export `os.O_ACCMODE`; use the available `O_WRONLY | O_RDWR` access bits. |
| 2 | 5 tests, 5.250s, FAILED (failures=17), exit 1 | The loader lazily imported its UTF-8-with-BOM codec while reads were guarded; preload that standard-library codec alongside other dependencies. Do not expand the data-read allowlist. |
| 3 | 5 tests, 6.758s, FAILED (failures=1), exit 1 | The client appended to the first run's usage log. Reset only the two owned output artifacts before each probe, so initial artifact states match. |

All failures were in the new test harness and are resolved. A sixth test added
the positive input-sensitivity control before the final passing runs. No existing
test or production implementation was changed. The Stage B fixture cleanup
completed; a final listing found no `tests/stage-b-*` directories.

Files created: the Stage B test file, this report, and `session-04-transcript.md`.
Updated: `progress-checkpoint.md` with an appended current-status entry. Previous
session logs are untouched; previous checkpoint content is preserved.

Limitations: Windows/Python 3.12 was exercised; Linux/Python 3.9 is unverified.
These tests do not establish model accuracy, production schema validation, or
future extraction/integration behavior. The baseline still reads only chats and
messages and does not consume the fixed model reply; its final output is tested
separately from the client probe. Later integration must apply the same boundary
checks to the actual orchestrated model pipeline. The guard is a Python regression
test, not an OS sandbox for arbitrary native code. No dependencies were added,
no real answer files were accessed, and no Stage C work was performed.
