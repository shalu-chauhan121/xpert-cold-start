# Session 03 — Stage A implementation

## Latest correction — validate immediately preceding context

The user identified that the original context check used a global set of earlier primary spans. That proved existence, but did not prove recency, order, or compliance with the configured overlap limit. The correction is limited to `data.py`, five additional synthetic tests in `tests/test_data.py`, this report, the checkpoint, and an append to the transcript. The loader, splitter, and exactly-once primary interval checks were not rewritten. Stage B remains unstarted.

`validate_window_coverage(data, windows, overlap_spans=2)` now retains a bounded, ordered tail of preceding primary spans **per chat**. Any supplied nonempty context must equal a contiguous suffix of that tail in its original order and contain no more than `overlap_spans` entries. Thus stale selections, skipped predecessors, reversed order, and excessive context fail validation. Existing evidence/chat checks still reject wrong-chat or unknown references. Empty context and shorter immediate suffixes remain valid because overlap is optional. A zero limit forbids all nonempty context.

This matches the existing builder's rule: the last N preceding primary spans, potentially crossing multiple earlier windows when each contains fewer than N spans. It does not restrict context to just the immediately previous window's primary tuple, which would contradict existing builder behaviour. A gap within the selected tail, however, is never permitted. This rule uses the existing deterministic per-chat record order, including its explicitly undated trailing partition; no timestamp is inferred.

`build_windows()` now passes its configured overlap value to the validator. The coverage report includes `overlap_spans`, so a caller revalidating custom assignments can explicitly reuse that setting. The standalone validator defaults to 2 and rejects negative, boolean, fractional, and noninteger limits. Its existing global `previous` set remains solely for duplicate primary detection, not context eligibility. The per-chat context history is capped at the configured count. All original primary interval coverage, incomplete-input handling, and evidence-preservation behaviour remains in place.

Actual commands, executed from `xpert-cold-start-starter/cold-start` on Windows/Python 3.12:

```text
# Before the validator fix, after adding the three requested regressions:
python -B -m unittest discover -s tests -p test_data.py -v -k context_overlap_rejects
Ran 3 tests in 0.034s
FAILED (failures=4)
Exit code: 1

# After the fix and two additional configuration/chat-isolation tests:
python -B -m unittest discover -s tests -v
Ran 44 tests in 0.475s
OK
Exit code: 0
```

The initial failures demonstrate the reported bug: all three test methods rejected the validator's false `succeeded` result, with two failing subcases in the stale/skipped-predecessor test. The final run includes all previous 39 tests plus five new test methods. The new cases cover stale and noncontiguous context, reversed context order, excessive overlap, configured limits 0/1/3 and invalid settings, optional shorter immediate suffixes, and per-chat history with interleaved chats. Negative context tests retain complete primary assignments and assert their primary counts/coverage remain intact. The existing long-span, empty/incomplete-input, duplicate-primary, and source-preservation tests also pass.

Stage A's reported context-validation gap is corrected. These are synthetic Windows results, not Linux certification or model-performance measurements. Character-based sizing, later extraction acknowledgements, runner integration, and earlier cleanup limitations remain as documented below. No API/model call, answer-file access, development-data run, or Stage B work occurred in this correction.

The earlier window implementation and its 39-test result below are retained as historical context; the latest result is the 44-test run above.

## Current completion update — primary window/span coverage

The user authorised completing the outstanding Stage A window/span requirement identified in `progress-checkpoint.md`. Before coding, the relevant approved-plan data-flow/input-contract/Stage A acceptance sections and existing `data.py` and `tests/test_data.py` were inspected. The plan requires exactly one primary assignment per message or long-message span, excluding contextual overlap. This requirement is now implemented and tested within `data.py`; the existing loader and unrelated modules were not rewritten. Stage A is complete at the data-module level. Stage B has not started.

This update supersedes the historical report's statements below that window/span assignment remains future work. The previous correction was valid at that time; the new authorised code closes that gap. Extraction, model calls, processing-job completion, and overall pipeline integration remain later-stage work.

### Changed files in this continuation

- `data.py`: added span/window records, deterministic window construction, independent coverage validation, and an assignment-completion gate.
- `tests/test_data.py`: added 14 synthetic tests to the existing 25; no replacement of earlier tests.
- `ai-logs/codex/session-03-implementation.md`: this completion update above the preserved historical report.
- `ai-logs/codex/progress-checkpoint.md`: updated current completion status, actual results, and next-stage boundary.
- `ai-logs/codex/session-03-transcript.md`: append-only actual conversation continuation with explicit coverage limitations.

No new runtime module was introduced. Read-only SHA-256 checks before/after the code work showed unchanged `solution.py`, `llm.py`, `schema.json`, `check.py`, `run.sh`, and the approved revised plan. No LLM/API call, development-input read, answer-key access, or solution run was performed in this continuation. Tests use synthetic records only; one existing test invokes the metadata-only data-loader CLI on synthetic input.

### Functions, data flow, and decisions

`load_input()` remains unchanged. Pass its `InputData` result to `build_windows()`, which returns a `WindowPlan` containing immutable window/span records and a coverage report. Future orchestration can call `WindowPlan.require_complete()` before using the assignments for extraction.

| Addition | Responsibility |
|---|---|
| `MessageSpan(message_id, start, end)` | Refers to original body characters in the half-open interval `[start, end)`. Python string offsets count Unicode code points, not bytes or tokens. The original message ID is never replaced with a synthetic span ID. |
| `ProcessingWindow(chat_id, primary, context)` | Holds tuples of primary spans and separate preceding-context spans from the same chat. Original chat IDs are preserved. |
| `WindowPlan(windows, coverage)` | Holds assignments and a validation snapshot. `require_complete()` raises on failed/incomplete status; it does not claim extraction has occurred. |
| `build_windows(data, max_primary_chars=4000, max_primary_spans=32, overlap_spans=2)` | Validates configuration; traverses chats in sorted ID order and each chat's existing ordered message index; splits only oversized bodies; packs primary spans within character/count limits; adds up to the requested number of preceding spans as context; validates the result before returning it. |
| `validate_window_coverage(data, windows)` | Independently checks references, chat membership, offsets, primary chronology, duplicate spans, contiguous full-body coverage, and permitted context reuse. Returns status, counts, rejected lines, undated IDs, and assignment errors. It checks source-body intervals rather than trusting the splitter's output list. |

Normal messages fit wholly in one primary window. A long message may necessarily participate in several windows: **each span**, not the whole long message, then has exactly one primary assignment. Adjacent spans share the original message ID and have contiguous offsets. There are no gaps, primary overlaps, or omitted characters. An empty body receives one `[0, 0)` span, so the message is still assigned once.

Context is copied by reference from preceding primary spans in the same chat; it does not increment primary coverage. The validator refuses context without an earlier matching primary span, duplicate context within a window, and wrong-chat/unknown evidence. Context cannot repair a missing primary assignment. Primary interval gaps, repeated intervals, overlaps, invalid offsets, empty-primary windows, and out-of-order primary records produce coverage errors.

The limits are conservative, configurable packing controls, not claimed model/API limits: at most `max_primary_chars` body characters and `max_primary_spans` primary units per window, plus at most `overlap_spans * max_primary_chars` context body characters. Metadata, prompt text, model tokens, and output allowance are not budgeted here. Model-aware budgeting remains Stage D/E work. Character splits can cross words or Unicode grapheme clusters; exact reconstruction is preserved, but this does not claim ideal linguistic segmentation.

No evidence text, timestamp, source bytes, or source dictionary is rewritten. A span's text is obtained by looking up its original message through `InputData.evidence()` and slicing its body with the recorded offsets. Sender, source line, raw bytes, and timestamp remain available through that record.

### Empty, undated, and incomplete input

- Valid empty inputs or a valid chat with no messages produce zero windows and `succeeded_empty` assignment status. `input_status` separately preserves the loader's state.
- Undated records still receive primary assignments in the loader's deterministic trailing undated partition. This is storage order, not a guessed timestamp or a claim about when they happened. Their IDs appear in `undated_message_ids`, and inherited input incompleteness blocks the completion gate.
- Malformed/duplicate/rejected records cannot be safely assigned invented IDs. Their original bytes remain in `InputData`; their source line numbers appear in the coverage report. Valid indexed records can still be assigned for inspection, but overall status remains incomplete.
- Missing/unreadable required inputs retain `failed`, even if some surviving messages have valid assignments. An all-rejected dataset is not reported as successfully empty.
- Assignment errors are separate from input issues: callers inspect `InputData.issues` for input details and the coverage report's `errors` for assignment defects. Successful assignment is not successful LLM processing or proof of semantic recall.

### Actual test run and review

Executed from `xpert-cold-start-starter/cold-start` on local Windows/Python 3.12:

```text
python -B -m unittest discover -s tests -p test_data.py -v

Ran 39 tests in 0.539s
OK
Exit code: 0
```

All 25 original tests and 14 added tests passed on this continuation's first run. This was a synthetic test run; no fresh development-dataset or Linux run is implied. The measured unittest duration is not a performance estimate.

The new tests cover exactly-once primary assignments across ordered chats, deterministic repeats, context-only overlap and chat isolation, long mixed-script text reconstruction, exact original IDs/metadata/bytes, an empty-body assignment, valid empty input, undated input, rejected/duplicate/malformed records, missing required files, invalid configuration, and deliberately corrupted assignments. Negative validator tests exercise gaps, duplicate primaries within/across windows, interval overlap, context-only omissions, repeated context, invalid offsets, unknown/wrong-chat evidence, and reversed chronological order. A single test also exercises 30 combinations of character limits, span-count limits, and overlap, including empty bodies and long multilingual messages, and checks bounds and exact reconstruction.

Code review confirmed that window construction advances for every primary unit, including empty-body spans; coverage checking is independent of packing; inherited input failure cannot be masked by full indexed-message assignment; and the original source structures are not mutated. No further code changes were needed after the passing run.

### Remaining limitations and stop point

No outstanding Stage A implementation item is identified within the approved input/evidence/assignment scope. Stage B remains the next stage and requires approval. Stage E processing acknowledgements and Stage G integration are not implemented. The baseline runner and the standalone loader CLI are unchanged; the latter still reports loading coverage only, while windowing is exposed through the Python functions.

Windows/Python 3.12 is the only environment tested. Linux/Python 3.9 compatibility, target-runtime budgeting, and hidden-data performance remain unverified. Previous inaccessible temporary directories remain a historical cleanup limitation; no cleanup was attempted here. Parsed source dictionaries and the coverage dictionary are mutable objects; treat them as read-only. Coverage is a snapshot, so future modified assignments must be revalidated against the original input.

## Historical report — original loading/indexing implementation

The following original report is retained for session history. Its 25-test result, initial development-input counts, and statements about then-pending window work describe the earlier implementation, not the current completion state above.

## Objective and authorised scope

Implement only input loading, message indexes, deterministic chronological ordering, evidence retention, and loading/indexing coverage. Use synthetic tests and the permitted development inputs. Do not implement later stages, make API calls, read answer files, or overwrite earlier logs.

The approved reference was `ai-logs/codex/session-02-revised-implementation-plan.md`. Its six runtime modules remain `solution.py`, `data.py`, `reasoning.py`, `tasks.py`, `llm.py`, and `validation.py`. This session adds only `data.py` to that architecture. The existing runner still uses the original baseline: it has not been integrated with the new loader. Tests and documentation are not additional runtime modules.

The starter project is `xpert-cold-start-starter/cold-start`. The actual development input directory is the sibling workspace path `xpert-cold-start/data/dev`, supplied to the loader as `../../xpert-cold-start/data/dev`. No answer files were opened. No solution run, checker run, prediction generation, or network call was performed.

## Files added

| File | Responsibility |
|---|---|
| `data.py` | Standard-library input loader, indexes, source records, diagnostic issues, evidence lookup, ordering, and a metadata-only command-line report. |
| `tests/test_data.py` | 25 synthetic unit tests, including a subprocess test of the loader's diagnostic command. |
| `ai-logs/codex/session-03-implementation.md` | This implementation report and actual verification results. |
| `ai-logs/codex/session-03-transcript.md` | Accessible user/assistant conversation text, with explicit coverage limitations. |

SHA-256 comparisons against the session's initial snapshot confirmed that all 17 pre-existing project files were unchanged, including `solution.py`, `llm.py`, `schema.json`, `check.py`, `run.sh`, and the five existing Session 01/02 reports and transcripts. The snapshot covers the starter project files, not every file elsewhere in the workspace. No Git diff was available because the inspected project was not a Git checkout.

## Data flow and important functions

The flow is: explicit input directory → three allowlisted file paths → preserved source records and seed → unique valid chats → participant IDs → unique structurally valid messages → ID/chat/sender indexes → chronological lists → quote diagnostics → coverage report.

An **index** is a dictionary that lets later code look up a message or its chat without repeatedly searching all messages. All three message indexes point to the same `InputRecord` objects; they do not create separate copies of message text.

| Definition in `data.py` | Explanation |
|---|---|
| `Issue` | Records a problem's input filename, physical line number where applicable, code, explanation, and severity. Warnings are distinguished from errors. |
| `InputRecord` | Retains a nonblank source line's exact bytes, filename, line number, parsed value, indexing flag, and separately validated timestamp. Invalid source lines remain available for diagnosis. |
| `InputData` | Holds source records, original seed, all indexes, participant IDs, file-read outcomes, and issues. |
| `load_input(input_dir)` | Main entry point. Reads, validates, indexes, and sorts; returns an auditable result even if some records fail. It never replaces missing inputs with a successful empty dataset. |
| `_permitted_path(folder, name)` | Accepts only `chats.jsonl`, `messages.jsonl`, and `seed.json`. Rejects an input root under a directory named `answers`, and rejects resolved input-file redirects outside the expected path. Does not enumerate the input directory. |
| `_parse`, `_unique_object`, `_reject_constant` | Decode UTF-8, accept an optional byte-order mark, parse JSON, and reject duplicate JSON object keys and nonstandard NaN/Infinity literals. This prevents silent JSON-key overwrites. |
| `_read_jsonl` | Reads JSON Lines one physical line at a time. Each nonblank line is an independent record. Keeps reading after a malformed line, retains its bytes, and records an issue. Missing/unreadable files make loading fail. |
| `_load_seed` | Retains the seed bytes and parsed object. Checks the basic shapes of circles, organisations, and goals. An empty object is valid; an empty file or malformed object is not treated as an empty signup. It does not classify people or resolve organisations. |
| `_unique_records` | Groups records by their exact original IDs. If an ID appears twice, excludes every occurrence from the unique index and reports each occurrence. This applies even to identical copies or an occurrence with bad metadata. |
| `_valid_timestamp` | Accepts finite numeric Unix seconds representable within Python's datetime range. Rejects booleans, strings, missing values, and out-of-range values; does not guess another time format. |
| `_order` | Orders dated messages by timestamp and then original source-line position. Puts undated records in a separate trailing group in source order. |
| `InputData.evidence(message_id)` | Returns the uniquely indexed original source record. Unknown, rejected, and ambiguous IDs raise `KeyError`; no substitute evidence is generated. |
| `InputData.require_complete()` | Raises `ValueError` for failed/incomplete loading. Future orchestration must call this gate before treating inputs as complete. It is not yet wired into the baseline runner. |
| `InputData.status`, `summary()`, `as_of` | Expose loading state, counts and diagnostics, and the latest valid timestamp respectively. `as_of` is `None` when no valid timestamp exists. It is not a trustworthy complete end-of-data time when loading is incomplete. |
| `main()` | Provides `python data.py <input_dir>`, which prints loading metadata, not the challenge output. Returns exit status 0 for successful loads, including successful empty loads; otherwise returns 1. |

## Preservation and validation decisions

IDs are checked for being nonempty strings but stored exactly, including any whitespace. IDs are never trimmed, renumbered, normalised, or fabricated. Original message bodies, unknown extra metadata, language/script, media placeholders, and reply IDs are retained. UTF-8 tests include English, Hindi, Bengali, Hinglish, emoji, and a long message. No translation or media interpretation is attempted.

The loader preserves both parsed records and exact original line bytes. Sorting changes index-list order, not the original record dictionaries or the source-record list. Future code must not mutate the original dictionaries; they are ordinary mutable Python objects rather than enforced immutable objects. Retained bytes provide an independent source representation.

Valid chat metadata supplies the person universe, including people who have no messages. `person_ids` excludes `ME`; the sender index includes `ME`. Empty chat and sender lists are retained. Message references to absent/invalid chats or globally unknown senders are rejected and reported. A globally known sender absent from that particular chat's participant list is retained with a warning. This avoids silently erasing an otherwise attributable message because of a local participant-list discrepancy.

Missing or invalid timestamps do not erase otherwise valid evidence. Such messages are indexed with a separate `timestamp=None`, retain their original timestamp field (or its absence), and make loading incomplete. Dated messages come first; undated messages follow in source order. That trailing placement is a deterministic storage convention, **not a claim that those messages happened later**. Equal known timestamps use source-line order, which is reproducible for the same input file and does not claim a finer real-world chronology.

Duplicate message/chat IDs are quarantined: all occurrences are preserved in source records, but none is selected as the authoritative indexed record. This deliberately favours traceable evidence over guessing which duplicate is correct. Duplicate chats also prevent their dependent messages from being indexed. Unknown quoted IDs produce a warning and stay unchanged; no missing reply is reconstructed.

Input kinds are checked against the inspected starter input contract: `text`, `voice_transcript`, `image_caption`, and `document`. This is input validation, not an implementation of the final output schema. Seed validation is structural only; semantic reconciliation belongs to a later stage.

## Coverage and empty-result policy

Coverage in this implementation means **read and indexed**, not extracted, interpreted, or included in an LLM window. One `InputRecord` is retained per nonblank physical message line. Blank lines are ignored as records but still count toward physical source-line numbers. There is no message truncation, filtering by language, or sampling.

Each record exposes `indexed`; the summary exposes nonblank lines seen, parsed object count, indexed message count, valid-timestamp count, undated IDs, rejected line numbers, per-file read completion, and issues. A failed read cannot establish how many unseen lines remain; counts honestly describe only lines seen before the failure.

| State | Meaning |
|---|---|
| `failed` | At least one required file was not completely read, including a missing file or rejected path. Any recoverable records remain available for diagnosis. |
| `incomplete` | All required files were read, but at least one error prevents a complete trusted load: malformed records, duplicates, invalid references, invalid seed structure, or invalid/missing timestamps. |
| `succeeded_empty` | All three required files were successfully read, no errors exist, and there are no indexed chats or messages. This describes the chat/message load; seed facts may still exist. |
| `succeeded` | Complete error-free loading with at least one indexed chat or message. Warnings can still be present. A valid zero-message chat is a successful load, not a failed stage. |

No output category is declared empty by this module. People/organisation/chat classification, goals, open loops, task ledgers, help decisions, windows, primary span assignment, and inference-stage coverage are unimplemented. The approved plan's long-message window/span acceptance condition remains future work: Stage A currently verifies that the entire long message survives loading without truncation. This boundary follows the user's specific Stage A loading/indexing coverage requirements.

## Tests and actual results

Tests create their own fictional chats/messages/seed and never use challenge answer-key data. `chat()` and `message()` are fixture constructors. `InputTests.setUp()` creates a unique disposable fixture directory; `write_inputs()` serialises fixtures; `codes()` extracts issue codes for assertions. Filesystem-boundary tests intercept file opens and simulate a redirected path; they do not access a real answers directory.

The 25 tests cover:

- Multiple chats, shuffled chronological order, timestamp ties, sender indexes, silent participants, and zero-message chats.
- Exact IDs, text, nested metadata, raw bytes, seed preservation, mixed scripts, long bodies, and invalid evidence lookup.
- Blank lines and physical source-line accountability.
- Valid empty data, each missing required file, and a nonexistent input directory.
- Malformed JSON, non-object JSON, invalid UTF-8 followed by valid records, duplicate JSON keys, and NaN literals.
- Identical/conflicting duplicate message IDs, duplicate chat IDs, and duplicate IDs where one occurrence has invalid metadata.
- Missing timestamps, invalid types/ranges, negative timestamps, fractional seconds, and refusal to coerce strings into dates.
- Missing/unknown quoted replies and all supported non-text message kinds.
- Invalid chat/message/seed structures and unknown chat/sender references.
- Three-file allowlisting, rejection of an answers-named input root, and rejection of a redirected input file.
- Diagnostic CLI nonzero exit on incomplete input, machine-readable coverage, and exclusion of message bodies from its report.

Executed from `xpert-cold-start-starter/cold-start` on the local Windows Python 3.12 interpreter:

```text
python -B -m unittest discover -s tests -v -f

Ran 25 tests in 0.352s
OK
Exit code: 0
```

The `-f` option stops on a failure; all 25 tests completed. `-B` avoids writing bytecode caches. The reported duration is the observed unittest result, not a benchmark or a claim about hidden-dataset runtime.

Two earlier attempts using `python -B -m unittest discover -s tests -v` failed with filesystem permission errors (25 tests attempted and 64 reported errors in each attempt, including subtest and cleanup errors). Python's temporary-directory creation produced inaccessible directories, first in the system temporary directory and then in the project tests directory. Merely changing location did not fix it. The final fixtures use uniquely named directories created with inherited permissions instead, and register cleanup for exactly the directory created by that test. No loader changes were needed to resolve these fixture errors.

The failed attempts left inaccessible temporary directories. Twenty-five `tests/stage-a-*` directories from the second attempt were listed; nonrecursive deletion attempts were denied. The system-temp directories from the first attempt were not subsequently enumerated or cleaned. Their contents could not be inspected; fixture-file writes reported permission errors. No permission bypass or elevation was attempted. The successful run removed its own new fixtures. These leftover directories are a local cleanup limitation, not additional implementation files.

The separate permitted development-input check was:

```text
python -B data.py '..\..\xpert-cold-start\data\dev'
```

It exited with code 0 and reported:

```json
{
  "status": "succeeded",
  "files_read_complete": {
    "chats.jsonl": true,
    "messages.jsonl": true,
    "seed.json": true
  },
  "chats_indexed": 138,
  "people": 286,
  "message_lines_seen": 4502,
  "message_objects_parsed": 4502,
  "messages_indexed": 4502,
  "messages_with_valid_timestamp": 4502,
  "undated_message_ids": [],
  "rejected_message_lines": [],
  "as_of": 1788715761,
  "issues": []
}
```

This establishes loading coverage for those allowed files only. It does not establish inference accuracy, scoring performance, Linux behaviour, or the full solution's 30-minute runtime.

## Remaining limitations and next approval boundary

- The baseline runner is unchanged and does not yet call `load_input` or `require_complete`. This session is a separately testable data-layer implementation.
- No Stage B or later-stage work was started. The loader's own basic answer-path protections were required explicitly for Stage A; end-to-end decoy independence and inference-import checks remain for Stage B.
- Primary window/span assignment and extraction coverage remain future work; load coverage must not be substituted for them.
- Dates are not guessed. Invalid inputs must be corrected or handled by an explicitly designed later recovery policy before a complete run is claimed.
- Raw dictionaries are preserved by convention, not an immutable container. Future consumers must avoid changing them.
- Tests ran on Windows/Python 3.12 only. Linux and Python 3.9 compatibility have not been executed or certified.
- The inaccessible directories from unsuccessful fixture setup remain to be cleaned outside this restricted session.
- No model performance, API capability, token cost, scoring improvement, or runtime estimate is claimed.

Stage A's requested loading/indexing/evidence functionality and synthetic tests are implemented. Stop here pending the user's approval for Stage B.
