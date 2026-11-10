**Session 01: Repository understanding — XPERT Lab Cold Start Internship Challenge**

Session date: 4 November 2026. Workspace: `C:\Users\Shalu Chauhan\OneDrive\Documents\Xpert`. Starter project: `xpert-cold-start-starter/cold-start/`. Local shell: PowerShell; the challenge execution target is Linux.

**Objective and scope.**

Understand the starter project before implementation, explain its behavior in beginner-friendly language, identify the major challenges and scoring priorities, and propose an implementation strategy. The user's follow-up explicitly authorizes this session document as the only file to create. Implementation and execution remain subject to later user approval.

This document records the inspection performed across the two user requests visible in this conversation. It contains the complete inspection report, both task prompts verbatim, and summaries of Codex's responses. It is not represented as a verbatim export of every assistant message or terminal result. No inaccessible conversations or earlier sessions have been reconstructed.

No solution, checker, or model call was executed during the inspection. Neither development nor example answer-key contents were opened. No implementation code was written. Read-only inspection commands listed files, read source/documentation, parsed input records for aggregate statistics, and extracted PDF text to standard output. No extracted PDF file was created. The only authorized write in the documentation follow-up is this Markdown document.

**Evidence and confidence.**

Verified source behavior comes from reading `run.sh`, `solution.py`, `llm.py`, `check.py`, and the actual `schema.json`. Challenge requirements come from the starter README, data README, write-up template, AI-log instructions, and supplied `Xpert_challenge.pdf`. Dataset statistics come from reading the input JSONL files, not from the answer key. Archive contents were listed without extracting or opening their answer entries.

The live challenge URL, `https://goals.xpert.chat/w/intern`, could not be opened by the browsing tool. The PDF is a saved snapshot dated 3 November 2026. Its deadlines and submission details are verified as statements in that snapshot, not confirmed as the latest live instructions. No challenge messages were sent to a website or a model endpoint during this inspection.

The inspection covered all starter source and documentation, the complete schema, the full example input, development input structure and aggregate checks, folder structure, archive inventories, and the PDF. It did not attempt a semantic interpretation of every development message. Answer files were intentionally excluded from content inspection; their purposes and documented format are explained using the READMEs and checker source.

**What the challenge requires.**

Xpert is a personal assistant in WhatsApp. The cold-start problem is learning enough about a new user from their conversation history to be useful without asking the user to manually describe everyone and everything in their life.

The program receives a directory of chats, messages, and a small amount of signup information. It produces one JSON file containing five arrays: people, organisations, chat assignments, goals, and open loops. Assistance decisions are nested inside open loops rather than stored in a sixth top-level array.

A circle is a person's relationship to the user. An organisation is something the user runs or belongs to, such as a company, home, society, or school. A goal is a broader intention or practice. An open loop is a task, obligation, pending answer, or decision whose progress needs tracking. The output must include final task status, even for tasks that became done or dropped during the supplied history.

The result is a structured interpretation and proposed assistance plan. The challenge does not ask the submitted program to actually contact people, book services, or set reminders.

**Repository structure and every file's purpose.**

The workspace currently contains two separately extracted packages. The actual starter project is nested under `xpert-cold-start-starter/cold-start/`, while the real development data is under `xpert-cold-start/data/dev/`.

| Workspace entry | Purpose |
|---|---|
| `Xpert_challenge.pdf` | Saved challenge brief, terminology, rules, scoring, submission requirements, and interview process. |
| `xpert-cold-start-starter.zip` | Original starter archive. Its entries were listed without extraction. |
| `xpert-cold-start.zip` | Original data archive. Its entries were listed without reading answer contents. |
| `xpert-cold-start-starter/` | Extraction container for the starter. |
| `xpert-cold-start-starter/cold-start/` | Actual starter project directory. |
| `xpert-cold-start/` | Extraction container for the data package. |
| `xpert-cold-start/data/` | Data package containing documentation and the development dataset. |

Paths in the following table are relative to the starter project directory.

| Starter entry | Purpose |
|---|---|
| `README.md` | Starter usage, input/output overview, scoring description, and model configuration requirements. |
| `run.sh` | Public command-line entry point used by the organisers. |
| `solution.py` | Deliberately naive baseline that reads input and writes predictions. |
| `llm.py` | Optional standard-library client for an OpenAI-compatible model API, with token logging. |
| `schema.json` | Exact formal output contract, using JSON Schema draft 2020-12. |
| `check.py` | Independent output validator and answer-based evaluator. |
| `WRITEUP.md` | Unfilled two-page submission template: focus, approach, cost, and expected failures. |
| `.gitignore` | Excludes `data/`, `*.zip`, `usage.jsonl`, `output.json`, `.env`, and `__pycache__/` from Git tracking in its scope. |
| `example/` | Small fictional dataset about Meera, separate from Arjun's development data. |
| `example/chats.jsonl` | Six example chats and their participants. |
| `example/messages.jsonl` | Twenty-nine example messages. |
| `example/seed.json` | Signup information: one known circle, one organisation name, and one goal. |
| `example/answers/` | Container for example evaluation labels. |
| `example/answers/answers.json` | Example answer key. Contents deliberately unopened. |
| `ai-logs/` | Required location for records of AI assistance. |
| `ai-logs/README.md` | Explains that AI transcripts, copied text, or screenshots should be included; AI use is expected. |
| `ai-logs/codex/` | Location for Codex session documentation. |
| `ai-logs/codex/session-01-repository-understanding.md` | This inspection and conversation record, created on the user's explicit follow-up request. |

Paths in the following table are relative to `xpert-cold-start/data/`.

| Data entry | Purpose |
|---|---|
| `README.md` | Describes the dataset, privacy expectations, incomplete development labels, and hidden evaluation. |
| `dev/` | Development input directory. |
| `dev/chats.jsonl` | Development chat metadata. |
| `dev/messages.jsonl` | Development conversation history. |
| `dev/seed.json` | Explicit signup facts that inference is allowed to use. |
| `dev/answers/` | Container for development evaluation labels. |
| `dev/answers/answers.json` | Development answer key. Contents deliberately unopened and not used for inference. |

No Git repository, `AGENTS.md`, automated tests, or dependency manifest was found in the inspected project. The workspace-level Git status command reported that the directory was not a Git repository. The starter uses Python's standard library and documents Python 3.9 or later. Python and Bash executables are present locally, but Linux execution and compatibility were not tested.

The README's relative `data/dev` example assumes the data is inside the starter directory. That is not the current layout. A later approved run can use the actual directory path, or the layout can be adjusted after permission to modify files. No data was moved. The starter `.gitignore` does not automatically protect a sibling data package if a Git repository is later created at the workspace root. Also, it ignores `output.json` specifically, while the README uses `out.json` in example commands. Submission hygiene should account for the actual paths and names.

During the initial inspection, the requested session-log path was observed as an empty, zero-byte file. During the follow-up pre-write inspection, it no longer existed. The reason for that external change is unknown. The file was absent immediately before this creation; no earlier content was overwritten, and no claim is made that Codex removed it.

**Execution flow from the entry point to output.**

The public interface is `./run.sh <input_dir> <output.json>`. This is documentation of the existing interface; it was not executed.

1. The caller supplies an input-directory path and an output-file path.
2. `run.sh` enables `set -euo pipefail`. These settings stop on shell command errors, reject unset variables, and propagate pipeline failures.
3. The script checks that exactly two arguments were passed. If not, it prints usage information to standard error and exits with status 2.
4. It invokes `python3`, locating `solution.py` relative to the shell script itself and forwarding both arguments.
5. Python's main guard checks the argument count and calls `main(input_dir, output_path)`.
6. `main()` turns the input path into a `Path` and reads `chats.jsonl` and `messages.jsonl` using `read_jsonl()`.
7. It collects unique participant IDs from chat metadata and excludes `ME`.
8. For each group chat, it invents an organisation whose ID is `org_` followed by the chat ID, copies the chat name, and assigns fixed attributes.
9. For each direct chat, it selects the first participant other than `ME` and assigns the chat to that person.
10. It constructs the five required arrays, assigning every person `friend` and leaving goals and open loops empty.
11. It serializes the object with indentation and writes UTF-8 JSON to the output path. `ensure_ascii=False` preserves non-ASCII characters in readable form.

Relative input and output paths are interpreted from the caller's current working directory; locating the script does not change that directory. The output parent directory is not automatically created. Input parsing and output writing errors are not handled with a recovery mechanism. The 30-minute limit is imposed by evaluation; `run.sh` itself contains no timer.

**How the four central files interact.**

| File | Actual interaction |
|---|---|
| `solution.py` | Reads chats and messages, builds predictions, and writes output. It does not currently import `llm.py`, read `seed.json`, load `schema.json`, or invoke `check.py`. |
| `llm.py` | Optional helper a future solution can import. It currently has no role in baseline execution. |
| `schema.json` | Declares the output contract. Neither Python script automatically loads it. |
| `check.py` | Separate program that reads inputs and an existing output, validates it, and optionally loads answers to score it. It is not called by `run.sh`. |

Inference means forming predictions using allowed inputs. Evaluation means comparing those predictions with reference answers afterward. The answer key belongs exclusively in the evaluation path; it must not influence inference at runtime or become a source of hardcoded identities.

If approved later, the intended expanded flow is: inputs and seed facts lead to interpretation, interpretation leads to evidence-backed structured results, and those results are validated and written. Model calls are optional parts of interpretation. Independent evaluation happens after output creation.

**Existing functions, baseline logic, and gaps.**

In `solution.py`, `read_jsonl(path)` reads every nonblank line as a JSON object and returns the records in a list. `main(input_dir, output_path)` implements all baseline processing and output writing. The main guard handles direct command-line invocation.

| Capability | What the baseline does | What is missing |
|---|---|---|
| People discovery | Collects participants from chats, excludes `ME`, sorts IDs. | No evidence aggregation across messages. |
| Circle classification | Assigns everyone `friend`. | No relationship reasoning and no seed application. |
| Organisations | Creates one per group chat. | No merging across related chats or distinction between actual organisations and other groups. |
| Organisation attributes | Uses `other`, `work`, and `member` for every organisation. | No inference of type, side, or user's role. |
| Chat assignment | Direct chat to the other person; group to invented organisation. | No group-to-person assignment or nuanced ownership. |
| Person links | Not produced. | `runs`, `supports`, and `looks_after` reasoning. |
| Goals | Empty array. | Discovery, classification, horizon, and evidence. |
| Open loops | Empty array. | Detection, ownership, dates, status tracking, and closure evidence. |
| Help | Not produced. | Assist/remind/leave decisions and their supporting details. |
| Message content | Loaded but unused. | All conversation understanding. |
| Seed | Not read. | Explicit known facts are ignored. |
| Robustness | Simple load-and-write flow. | Recovery, model reply checks, and runtime/cost controls if model calls are added. |

There are no literal unfinished `pass` functions, `TODO`/`FIXME` markers, or `NotImplemented` exceptions in the inspected source. The placeholders are semantic: fixed default classifications and empty results. `WRITEUP.md` is a documentation template still awaiting content.

The direct-chat rule assumes there is at least one non-`ME` participant. The supplied dev direct chats each have exactly one such participant, but malformed or different future inputs were not tested. The naive organisation rule is contrary to the broader task semantics: a group can belong to a person, and several chats can belong to one organisation.

In `llm.py`, `chat(messages, model=None, temperature=0, max_tokens=None, response_format=None, timeout=120)` is implemented. It reads `LLM_BASE_URL`, `LLM_API_KEY`, and normally `LLM_MODEL` from environment variables. An environment variable is a configuration value supplied to a running process without embedding it in source code. The helper allows an explicit model override; a submitted solution should still respect the organiser's model configuration.

The helper sends JSON to the configured base URL plus `/chat/completions`, authenticates using the key, reads the response, and returns `choices[0].message.content` as text. It optionally passes `max_tokens` and `response_format` through to the endpoint. This does not itself guarantee that the reply is valid challenge output.

After a successful response, it appends model name, prompt tokens, completion tokens, and elapsed seconds to `usage.jsonl` in the current working directory. A token is a unit of text processed by a model; it is not exactly a word. Missing provider usage fields are logged as null. The log appends across calls and runs, so later cost reporting must identify run boundaries. It does not calculate dollar costs, include all possible provider billing categories, or record failed requests reliably. There are no retries, caching, batching, or automatic structured-reply validation.

`check.py` is an evaluator rather than an unfinished inference module. Its functions are:

| Function | Responsibility |
|---|---|
| `read_jsonl()` | Parse line-based input records. |
| `load_input()` | Load chats, messages, optional seed, and optional answers. |
| `validate()` | Check output structure, allowed values, identifier references, and chat coverage. |
| `f1()` | Combine precision and recall. |
| `jaccard()` | Measure overlap between two sets. |
| `org_members()` | Represent an organisation by attached chat and person IDs. |
| `match_orgs()` | Pair predicted and reference organisations by overlap. |
| `score()` | Calculate the seven automatic scoring components. |
| `main()` | Read output, report validation errors, and print scores when answers exist. |

No baseline score was measured in this session. The starter README says its example performs well on chat assignments and poorly elsewhere; that is not evidence of the same performance on the full development dataset.

**Input formats and observed dataset properties.**

JSON is a format for structured objects, arrays, strings, numbers, booleans, and null. JSONL means one complete JSON object per nonblank line. A JSONL file is not one large array wrapped in square brackets. The readers skip blank lines and parse each remaining line independently.

| Input | Field | Meaning |
|---|---|---|
| Chats | `chat_id` | Stable chat identifier in the input. |
| Chats | `name` | Chat display name. |
| Chats | `is_group` | Boolean indicating a group or direct chat. |
| Chats | `participants` | Person IDs belonging to the chat. |
| Messages | `id` | Message identifier. |
| Messages | `chat_id` | Chat containing the message. |
| Messages | `sender_id` | Sender's person ID; `ME` identifies the user. |
| Messages | `sender_name` | Saved sender name, which is a clue rather than a unique identity key. |
| Messages | `ts` | Unix timestamp in seconds: elapsed time from the Unix epoch. |
| Messages | `kind` | `text`, `voice_transcript`, `image_caption`, or `document`. |
| Messages | `body` | Supplied text content or media representation. |
| Messages | `quoted_id` | Replied-to message ID or null. |
| Seed | `circles` | Mapping of known person IDs to circles. |
| Seed | `organisations` | Known organisation names. |
| Seed | `goals` | Goals explicitly supplied at signup. |

Use IDs rather than names to track people. The example user is Meera and the development user is Arjun, but both are represented by `ME`. Names are changed again on hidden evaluation. Message IDs should be treated as identifiers, not a substitute for timestamp ordering; the example begins with later-numbered IDs before earlier-numbered ones.

| Development input property | Verified observation |
|---|---:|
| Messages | 4,502 |
| Chats | 138 |
| Group chats | 64 |
| Direct chats | 74 |
| Unique participant IDs excluding `ME` | 286 |
| Text records | 3,802 |
| Image-caption records | 606 |
| Document records | 94 |
| Voice-transcript records | 0 |
| Non-null quoted IDs | 0 |
| Seeded circles | 10 |
| Seeded organisation names | 2 |
| Seeded goals | 0 |

The first message timestamp is 24 August 2026, 01:31:02 UTC; the last is 6 September 2026, 17:29:21 UTC. These aggregate values were calculated during the initial read-only inspection and were not inferred from README approximations.

Structural checks found no duplicate chat IDs, no duplicate message IDs, no messages pointing to unknown chats, and no sender IDs absent from the overall chat participant list. Each direct chat has exactly one participant other than `ME`. These checks do not prove that every sender belongs to that message's specific chat, or that all text is complete; no broader claim is made.

Some media records contain only `[photo]`, `[video]`, or `[document]`. The underlying attachment contents cannot be inferred from those markers. No attachment downloads are required by this inspected format. The absence of reply references and voice transcripts in dev does not mean those features can be ignored on hidden inputs.

The data README says reference circles cover only people the user has classified, and that development task labels come from an existing system and are imperfect. It explicitly says goals and help actions are unlabelled in dev. These are documentation statements, not observations from opening the answer key.

The README documents that answer loops use `source_msgs` for acceptable origins, `closing_msgs` for closure evidence, and a help-action string with a `why`, rather than precisely the prediction format. Hidden answers can also contain `loops_scored_from`. These details explain checker behavior and do not authorize reading answers during inference.

**The actual output schema.**

The inspected schema uses JSON Schema draft 2020-12. A schema is a formal contract for data shape. An enum means a value must be selected from an explicit allowed list. A required field must be present. An optional field may be omitted, but when present must still satisfy its declared type. Null means no value, which differs from an empty string.

The output is one object with exactly five required top-level arrays: `people`, `organisations`, `chats`, `goals`, and `open_loops`. Unknown top-level properties are forbidden. Every declared nested object also uses `additionalProperties: false`. Do not add confidence, explanation, or debugging fields to those objects unless the schema allows them. Internal analysis can carry extra information before final serialization.

**People array.** Each item requires string `id` and enum `circle`. The intended contract says one entry per relevant person and never `ME`.

Allowed circles: `spouse`, `child`, `parent`, `in-law`, `sibling`, `relative`, `friend`, `colleague`, `client`, `vendor`, `partner`, `staff`.

Optional `links` is an array of objects, each requiring string `organisation` and enum `link`, with `link` either `runs` or `supports`. Organisation references should point to the solution's own organisation IDs. Optional `looks_after` is an array of person-ID strings, for staff who look after particular people.

The PDF defines a circle as one relationship to the user across all chats. It is not a closeness rating: a household cook and office cleaner can both be `staff`. `runs` means someone helps run an organisation with the user, while `supports` describes service/support work for it.

**Organisations array.** All five fields are required:

| Field | Allowed value |
|---|---|
| `id` | String chosen by the solution. |
| `name` | String name. |
| `type` | `company`, `residence`, `vacation home`, `workspace`, `society`, `school`, `other`. |
| `side` | `home`, `work`. |
| `role` | `owner`, `partner`, `helper`, `resident`, `parent`, `member`, `other`. |

The role describes the user's role in that organisation. The PDF says a client's company is not an organisation merely because it is mentioned; the client is represented as a person in the client circle. Organisation names and chosen IDs need not match the answers because matching uses associated chats and people.

**Chats array.** Each item requires string `chat_id`, plus exactly one of string `person` or string `organisation`. The `oneOf` rule makes the choice exclusive: neither or both is invalid. The task requires every input chat to be assigned exactly once. A group can belong to a person; the PDF's example is a child's class parents' group belonging to the child. The starter's group-to-organisation rule is therefore only a naive default.

**Goals array.** There may be at most ten items. Each requires string `title`, enum `area`, enum `type`, enum `horizon`, and array `evidence` with at least one message-ID string.

| Goal field | Allowed values |
|---|---|
| `area` | `self`, `spouse`, `kids`, `parents`, `work`, `friends`, `experiences`, `finances`, `health`, `home`. |
| `type` | `habit`, `milestone`, `experience`. |
| `horizon` | `3mo`, `1yr`, `3yr`, `5yr`. |

A habit is a repeated practice, a milestone is a target, and an experience is something to plan and do. As an illustrative distinction, exercising regularly is a broader goal, while sending a training plan is a task. This is an explanation, not an inferred label for a development person. Seed goals do not necessarily contain evidence fields, so simply copying a seed goal into output can violate the output contract unless message evidence is attached.

**Open-loops array.** The name describes the category of tracked work, not a restriction that every item must still be open.

| Field | Formal schema requirement |
|---|---|
| `title` | Required string. |
| `type` | Required enum: `commitment`, `followup`, `deadline`, `question`. |
| `owner` | Required string: semantically `ME` or the person who owes the action. |
| `chat_id` | Required string referencing an input chat. |
| `source_msg` | Required string referencing the originating message. |
| `status` | Required enum: `open`, `done`, `dropped`. |
| `due` | Optional string or null; described as `YYYY-MM-DD`. |
| `closed_by` | Optional string or null; intended as the message proving completion or cancellation. |
| `help` | Optional object or null; intended only for open loops. |

A commitment is a promise, a followup is something the user is waiting on, a deadline is date-bound work, and a question is a pending answer or decision. Status is judged at the end of the supplied data, not at the computer's present date.

When `help` is an object, `action` is required and must be `assist`, `remind`, or `leave`. Its other allowed properties are string `next_step`, boolean `needs_yes`, string `remind_at`, and string `reason`.

| Action | Task-level expected details |
|---|---|
| `assist` | A one-line next step and whether that step needs the user's yes. The PDF distinguishes private/reversible preparation from external or irreversible action. |
| `remind` | A suitable reminder time as an ISO date-time string. |
| `leave` | A reason to stay out: someone else's responsibility, excessive sensitivity, or likely annoyance. |

**Task requirements, schema constraints, and checker validation are not identical.**

The schema formally requires only `action` in a non-null help object. It does not conditionally require `next_step`/`needs_yes`, `remind_at`, or `reason`, although the task asks for them. Date formats are described without formal `format` or `pattern` constraints. The schema does not require `closed_by` when status is done or dropped, and does not structurally restrict help to open statuses. Those are semantic obligations in the brief and descriptions.

`check.py` implements its own checks instead of importing a JSON Schema validator. It checks input references, duplicate people/organisations/chat assignments, missing chat assignments, allowed enums, evidence existence, and help only for open loops. It does not enforce every nested property restriction or type. It does not enforce complete people coverage, require closure evidence for every closed loop, verify that a loop's source message belongs to its listed chat, or prove that a cited message actually supports the claim. Some malformed nested structures can also raise exceptions rather than produce a tidy validation error.

Passing this checker alone is not proof of full schema compliance or semantic correctness. The proposed solution should satisfy the written task, the actual schema, and reference-integrity checks together.

**Challenge requirements and scoring.**

| Component | Points | Basis |
|---|---:|---|
| Circles | 12 | Correct circle for labelled, non-seeded people. |
| Organisations | 8 | Overlap of attached chats and people, accounting for missing and extra organisations. |
| Chats | 8 | Correct person assignment or matched organisation assignment. |
| Goals | 8 | Goal area plus shared evidence, balanced precision and recall. |
| Open loops found | 14 | Acceptable source-message matches, balanced precision and recall. |
| Open loops closed right | 14 | Correct final status, with a penalty for falsely closing genuinely open work. |
| Where to help | 10 | Correct action, with a penalty for intervention when the right action is leave. |
| Cost | 12 | Dollars per 1,000 messages, measured by organisers. |
| Write-up | 7 | Focus, approach, cost, and particularly how predicted failures match actual ones. |
| Runs with one command | 7 | Clean execution within the time limit. |
| Total | 100 | Automatic categories total 74; the other categories total 26. |

Precision is the fraction of predictions that are correct. Recall is the fraction of reference items found. F1 is their harmonic mean: `2 × precision × recall / (precision + recall)`, with zero returned when the relevant counts are zero in the helper. This means making many speculative predictions can reduce the score even if some additional real items are found.

Circle scoring divides correct circles by labelled answer people excluding IDs already supplied in seed circles. Missing a scored person loses credit. Seeded facts still matter for coherent output and later reasoning, even though copying them earns no circle points.

Organisation membership combines chat IDs and person IDs from links. Jaccard similarity is the number of shared members divided by the number of distinct members in either set. The checker sorts candidate pairs by similarity and greedily accepts positive-overlap pairs one-to-one; it does not compute an optimal global assignment. The organisation score is the sum of selected similarities divided by the larger predicted/reference organisation count. Names, type, side, and role are not used in this overlap calculation. Empty or fragmented organisations are therefore not useful shortcuts.

Chat scoring compares direct person IDs or the predicted organisation selected by that pairing. Organisation discovery affects both organisation and chat scores.

A goal matches when its area matches and it shares at least one evidence message with an unused reference goal. Matching is one-to-one. For seeded goals, the checker identifies reference goals by seed-title equality and removes predictions matching those reference goals by area and evidence. The remaining goals use F1. Titles, types, and horizons still must satisfy the task, but they are not the goal-matching test in this checker.

A loop is found when its predicted `source_msg` occurs in an unused answer loop's accepted `source_msgs`. Title similarity, owner, and type do not decide the match. Accurate source selection is therefore essential. Duplicate predictions can harm precision. The loop-found component uses F1 over matched, predicted, and reference loop counts.

For matched loops, correct status earns 1. A wrong status when the reference is open costs 1; other wrong statuses earn 0. The total is divided by all reference loops, including missed loops, then floored at zero. Predicting done or dropped without evidence can erase gains from correct statuses.

Help scoring considers reference loops that are open and have help labels. A matching action earns 1. Predicting assist or remind when the reference says leave costs 1. The score is divided by all such labelled loops and floored at zero. The prediction must also remain open for its help action to count. Detection and status quality therefore directly affect achievable help points.

The checker does not directly score every descriptive field, including closure-message accuracy, organisation attributes, the exact goal wording, or assistance detail quality. These remain required aspects of a useful, compliant result; the recommendation is to meet the task rather than exploit validation gaps.

The data README states that goals and help are unlabelled in dev. The remaining listed automatic categories sum to 56 points rather than 74. The actual printed denominator is dynamic: the checker skips categories whose score is `None`. No score or denominator was measured by executing the checker in this session. A dev total alone cannot establish hidden performance in goals and help.

The brief describes roughly eight weeks and 20,000 messages overall. The first two weeks form dev; roughly 15,000 messages over the following six weeks form hidden evaluation. Names are changed again in the hidden set, so hardcoded development identities are not a transferable solution. Earlier hidden weeks are context; loop scoring concerns the final two weeks.

When `loops_scored_from` exists, predicted loops are retained only if their source timestamp is at or after the cutoff. Answer loops are retained only if the earliest timestamp among their accepted sources is at or after the cutoff. The cutoff comes from evaluation answers; inference should not read answers to obtain it or assume that it is provided as an input field. The task still requests loops from the data, with the evaluator deciding which ones count.

The supplied PDF states that evaluation uses a clean container, no internet except the model endpoint, one run, and a 30-minute limit. Code must read `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. Testing keys are the participant's responsibility; organisers use their own key for grading. Fine-tuned and self-hosted models are prohibited. Ordinary rules, regular expressions, embeddings, and small local libraries are welcomed by the brief, subject to the execution restrictions. No particular model, provider, budget, or dependency has been selected in this session.

The submission is a GitHub repository containing code and the `run.sh` interface, `WRITEUP.md` of at most two pages, and `ai-logs/` records. The PDF lists 12 November 2026 at 23:59 IST as the deadline. It says a private repository is acceptable if `rmaslunia` is added, the exact commit and model must be specified, and the latest submission before the deadline counts. These are snapshot statements awaiting any newer organiser guidance.

The rules require solo work; participants may discuss ideas but must not share code or results. AI assistance is expected and documented. Data must not be committed or shared, attempts to identify the underlying person are prohibited, and the data should be deleted when the challenge ends. The program may send data only to the model endpoint. The PDF also describes shortlisted interviews from 16 November, including a code walkthrough and a live correction exercise using the candidate's AI tools.

**Highest-value components and major technical challenges.**

Loop detection, status, and assistance together account for 38 points, the largest related block. People, organisations, and chats account for 28 points and provide context needed for good task ownership and help decisions. Goals account for 8 points. Cost and one-command execution together account for 19 points, while the write-up accounts for 7. These totals are arithmetic from the published rubric, not a guarantee that any category is easy.

1. Relationships are ambiguous. Names, honorifics, and friendly language can mislead. A service worker can be addressed affectionately without being a relative. Evidence needs to be combined across chats, with seed facts providing anchors.
2. Organisations require grouping. Several groups can concern the same company or home, while a group can belong to a person. Mentioning a client company does not automatically create an organisation.
3. Tasks evolve. Requests can be acknowledged, delayed, revised, fulfilled, cancelled, or reopened. An okay or silence is not necessarily closure. Status must reflect the end of the supplied history.
4. Ownership differs from authorship. The sender can be requesting work from someone else. Many tasks in a group are not Arjun's responsibility or appropriate for his assistant to manage.
5. Evidence selection affects matching. The right task description with the wrong source ID can miss a reference match. Summaries must retain source IDs instead of losing provenance.
6. Context can be incomplete. The brief describes English, Hindi, Bengali, and Hinglish; media placeholders reveal little, and all dev reply references are null. The system must handle uncertainty without inventing facts.
7. Relative dates need a temporal anchor. Tomorrow and Friday should be interpreted relative to the message, with a justified timezone policy, rather than the machine's present date.
8. Goals differ from individual tasks and advertisements. Repeated discussion can indicate a personal intention, but a forwarded event promotion is not automatically a goal. Only evidence-backed goals should be emitted.
9. Generalisation matters. Hidden names change, and the available development labels are incomplete and imperfect. Rules should describe transferable patterns, not memorized answer entities.
10. Cost and runtime constrain reasoning. Repeatedly sending the entire history, or issuing a model call per message, can be expensive and slow. Batching must preserve conversational context.
11. Evaluation is partial. Goals and help cannot be tuned against absent dev labels. Manual review and carefully separated evaluation will be needed after execution is approved.
12. Corrections should be manageable. The interview includes a live correction. A clear separation of seed facts, inferred relationships, task state, and serialization should make later corrections easier to apply consistently.

**Recommended implementation strategy — proposed only, not implemented.**

1. Establish the input/output foundation. Read UTF-8 JSONL and seed data, preserve all IDs, organise messages by chat and timestamp, and build lookup tables. A lookup table maps an ID to its record so later steps can resolve evidence without repeatedly searching the entire file. Keep answer access outside inference. Validate both schema shape and input references before writing output.
2. Build the people–organisation–chat model. Apply explicit seed facts first. Aggregate evidence about each person and organisation across conversations. Use ordinary code for unambiguous structure and model reasoning for ambiguous language. Merge supported organisation identities and allow group-to-person assignments.
3. Extract candidate loops in conversation batches. Retain neighbouring messages and speaker identities. Batching means processing related messages together to reduce repeated context and API overhead. Every candidate should preserve its source message, owner, type, and any due-date evidence.
4. Track candidates through later messages. Reconcile duplicates, revisions, completion, and cancellation. Keep enough task state across batches to avoid forgetting prior promises. Require supporting evidence for closure and determine final status at the dataset endpoint.
5. Decide assistance after status and responsibility are understood. For open loops, distinguish private preparatory work, reminders only the user can act on, and matters best left alone. Include the action-specific fields requested by the brief even where the schema does not mechanically require them.
6. Extract a small set of supported goals. Distinguish habits, milestones, and experiences from routine tasks. Attach real evidence, select area and horizon carefully, and keep the list within ten items. Do not manufacture goals to fill the limit.
7. Evaluate incrementally after approval. Start with the small example, then run the development dataset. Score predictions separately using the supplied checker; do not let its labels enter inference. Inspect representative errors and improve general rules. Use manual review for dev goals and assistance because those labels are absent.
8. Control cost, robustness, and runtime from the start. Measure tokens and elapsed time, estimate dollars from verified provider pricing when a model is chosen, batch related requests, reuse derived context within a run, and handle failed or malformed model responses. Any later caching must preserve correctness and respect clean evaluation rather than depend on development answers or previous runs.
9. Prepare the submission continuously. Keep AI-session records, document failure categories and approximate rates once measured, and eventually check clean Linux execution and the one-command contract. Make predicted weaknesses honest and specific instead of claiming unmeasured accuracy.

Recommended order: a valid end-to-end foundation, then relationships and chat organisation, followed by loop detection, status, and help. Goals can be developed alongside these once evidence handling is reliable. This ordering is a judgement based on dependencies and points, not an organiser-mandated sequence. No implementation step above has been performed or approved yet.

**Assumptions, uncertainties, and unresolved questions.**

| Topic | Verified fact | Unresolved question or proposed handling |
|---|---|---|
| Current official instructions | The local PDF and READMEs were inspected; the live page was inaccessible. | Are there newer FAQs or changed requirements? Do not present snapshot details as independently verified current rules. |
| Cost scoring | Cost is 12 points, measured in dollars per 1,000 messages. | The exact point conversion, thresholds, and budget are absent. No target cost is invented. |
| Organiser baseline | The PDF says baseline score and cost would be published. | No actual figures were found in the supplied files. The starter's qualitative claims are not a measured baseline here. |
| Timezone | Timestamps are Unix seconds; an output example uses `+05:30`. | No universal timezone-resolution policy is specified. IST is a possible later assumption, not an established dataset rule. |
| Dev duration | Actual timestamps and the data README support two weeks. | The PDF download section also says week 1. Treat this as an inconsistency and prefer the actual data span when describing these files. |
| Seed size | Actual dev seed has ten circles, two organisation names, and no goals. | The general PDF describes about 20% of people and one goal. Code should read actual seed contents rather than assume those quantities. |
| Hidden labels | The README says hidden goals/help are hand-labelled. | Their exact contents and the precise cutoff are unavailable and should not be guessed or obtained through answer access. |
| Model choice | An OpenAI-compatible API and environment-variable configuration are required. | Provider, model, spend limit, and credentials have not been selected. No current pricing claim is made. |
| Runtime and accuracy | Source behavior was inspected. | No solution run, checker run, API test, benchmark, or score exists from this session. |
| Session-file state | It was empty in the first inspection and absent before creation in the follow-up. | The cause of the intervening filesystem change is unknown; it was not attributed to the user or Codex. |

Codex asked whether newer organiser instructions, a published baseline, or a detailed cost-scoring rubric were available. No answer to that question is visible before this document was written. The follow-up request authorizes documentation only and does not constitute implementation approval.

**Conversation provenance and exact user task prompts.**

The two blocks below reproduce the task prompts visible to Codex in this conversation. They do not include hidden system/developer instructions. A separate environment-context message supplied the working directory, PowerShell shell, date, Asia/Calcutta timezone, and filesystem permissions; those are summarized at the start rather than represented as an additional authored task prompt. The report does not claim access to conversations from other sessions.

First user task prompt, verbatim:

```text
I am participating in the XPERT Lab Cold Start Internship Challenge.

I want you to act as my technical mentor and coding assistant throughout this project. I am starting from scratch, so guide me step by step and explain technical concepts clearly.

Before doing any implementation, I want you to understand the project completely.

**FIRST TASK: REPOSITORY INSPECTION**

1. Inspect the complete starter repository.
2. Explain the purpose of every file and folder.
3. Explain the execution flow from `run.sh` to the final JSON output.
4. Explain how `solution.py`, `llm.py`, `schema.json`, and `check.py` interact.
5. Identify incomplete functions, placeholders, and existing baseline logic.
6. Explain the input JSONL files and the expected output schema.
7. Explain the challenge requirements and scoring system. Identify which components are most important.

**IMPORTANT RULES:**
- Do not modify any files.
- Do not write or generate code yet.
- Do not execute or run the solution.
- Do not use the development answer key for inference.
- Do not assume anything about the schema; inspect the actual `schema.json`.
- Explain technical concepts in beginner-friendly language.
- Clearly distinguish verified facts from assumptions.
- If anything is unclear or missing, ask me instead of guessing.

At the end, provide:
1. A clear summary of what the challenge requires.
2. A breakdown of the existing starter implementation.
3. The major technical problems we need to solve.
4. A recommended implementation strategy.

Wait for my approval before proceeding to implementation.
```

Summary of Codex's response to the first prompt: Codex announced a read-only inspection, inspected all starter source and documentation plus the schema, read example inputs and development metadata, gathered aggregate input statistics, listed ZIP entries, and read the PDF without writing an extracted file. It reported the naive baseline, the separation of inference and evaluation, differences between schema and checker, scoring formulas and priorities, real data limitations, submission requirements, and a phased proposed strategy. It explained that answers were unopened, no solution or checker had run, and implementation would wait for approval. It also disclosed the inaccessible live page and requested newer organiser material.

The clarification question sent through the user-input tool was exactly:

```text
Do you have any newer organizer instructions, a published baseline score/cost, or a detailed cost-scoring rubric? The supplied files do not include those, and the live challenge page was inaccessible.
```

Second user task prompt, verbatim:

```text
I am participating in the XPERT Lab Cold Start Internship Challenge.

Act as my technical mentor and coding assistant throughout this project. I am starting from scratch, so explain technical concepts clearly and guide me step by step.

## FIRST TASK: COMPLETE REPOSITORY INSPECTION

Before implementation:

1. Inspect the complete starter repository.
2. Explain the purpose of every file and folder.
3. Explain the execution flow from `run.sh` to the final JSON output.
4. Explain how `solution.py`, `llm.py`, `schema.json`, and `check.py` interact.
5. Identify incomplete functions, placeholders, and existing baseline logic.
6. Explain the input JSONL files and expected output schema.
7. Explain the challenge requirements and scoring system.
8. Identify the highest-value components and major technical challenges.

## DOCUMENTATION REQUIREMENT — IMPORTANT

After completing the inspection, automatically create:

`ai-logs/codex/session-01-repository-understanding.md`

This file must contain:

- The objective of this Codex session.
- The complete inspection report.
- Repository structure and file explanations.
- Execution flow.
- Input and output schema explanations.
- Challenge requirements and scoring breakdown.
- Existing implementation and identified gaps.
- Technical challenges and recommended implementation strategy.
- Important assumptions and unresolved questions.
- The exact prompts given to Codex during this session and a summary of its responses.

Make the documentation detailed enough that another developer can understand the session without reading the terminal history.

Do not fabricate conversation content or claim to have saved conversations you cannot access.

## STRICT RULES

- Do not modify existing project files.
- Do not write implementation code.
- Do not execute or run the solution.
- Do not use the development answer key for inference.
- Inspect the actual schema rather than making assumptions.
- Distinguish verified facts from assumptions.
- Do not overwrite unrelated files.
- Only create the requested session documentation file.

At the end, show me the documentation file path and confirm what you included.

Wait for my approval before proceeding to implementation.
```

Summary of Codex's response to the second prompt up to document creation: Codex agreed to save the report and both visible task prompts, checked the target path to avoid overwriting content, found it absent, and re-read the actual schema and central source files. It took an in-memory SHA-256 snapshot of existing non-answer starter and data files for a later read-only comparison; this snapshot did not create another file. It then prepared this detailed documentation, keeping verified facts, proposed work, and open questions separate. This is a response summary, not a claim that a full chat export or terminal transcript was saved.

**Handoff state.**

Repository understanding is documented. The starter implementation remains unchanged. There is no measured baseline score or runtime from this session. The next implementation step requires the user's approval. Until then, the proposed strategy is only a plan, and the answer key remains outside inference.
