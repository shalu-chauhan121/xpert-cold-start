**Session 02 — Revised implementation plan**

Status: proposal awaiting user review and approval. The current clarification request authorizes edits to this plan and an append-only continuation of `session-02-transcript.md`. No source code, test code, prompt implementation, model call, answer-key access, or solution execution is part of this revision. The original architecture report, Session 01 records, and existing transcript contents remain unchanged.

**Recommendation: six runtime modules, one model, and a task ledger.**

The previous architecture has useful ideas but splits them into too many files for a first implementation. Keep its evidence preservation, separate inference/evaluation, and chronological task tracking. Remove separate configuration, telemetry, cache, exporter, goal, help-policy, and record modules. Those responsibilities are small enough to live in six modules initially. Do not add agents, a database, embeddings, persistent caches, or a general workflow framework.

The objective is a working implementation of all five categories, not five arrays containing mostly placeholders. People, organisations, chat assignments, goals, and open loops must each have a real inference path. An empty goal/task list is acceptable when supported by the input, not when that stage failed or was never implemented.

Verified constraints retained from the inspected starter: the exact five output arrays and allowed fields come from `schema.json`; each chat has exactly one person/organisation target; people exclude `ME`; goals require evidence and are limited to ten; loops include open/done/dropped states; the brief asks for closure evidence and help details; the run has a 30-minute limit and uses the configured model endpoint. Dev goals/help are unlabelled. No additional accuracy target, spending limit, provider feature, or benchmark result is claimed here.

This plan deliberately replaces the earlier illustrative price and latency examples with formulas driven by measured request usage and elapsed time. Model, account limits, prices, and tokenizer behavior remain unknown until verified for the configured endpoint.

**1. Remaining modules and their boundaries.**

All paths below are proposed future implementation paths relative to the starter project. The two existing Python runtime files would need integration changes after approval; four Python runtime files would be added. The launcher-level deadline integration described in section 9a may also require a small future `run.sh` change, while preserving its public interface.

| Runtime module | Responsibility | Explicit boundary |
|---|---|---|
| `solution.py` — existing | Parse the existing two arguments; hold simple configuration; run stages in order; maintain coverage and run summary; enforce global deadline; assemble, validate, and atomically write output. | Does not interpret language or read answers. No separate orchestrator, config, or exporter module. |
| `data.py` — new | Read the three allowed inputs; retain raw messages; index IDs; sort chats; create windows; retrieve original evidence and candidate context. | No API calls and no directory-wide file discovery. |
| `reasoning.py` — new | Keep a small set of versioned prompt templates and model-response contracts; extract observations; resolve organisations/people/chats/goals; review task links and help choices in batches. | Returns proposed decisions with evidence. Does not silently mutate task state. No separate module per output category. |
| `tasks.py` — new | Store task records and chronological events; generate candidate matches; request semantic review through `reasoning.py`; validate and apply supported operations; produce final task states. | Owns task identity/state. Similar titles or shared source IDs alone do not merge tasks. |
| `llm.py` — existing | Be the single HTTP client; read required environment variables; retain response metadata; track calls/tokens/time; perform bounded retries; deduplicate identical successful requests in memory. | Only runtime network boundary. No second endpoint/model and no duplicate retry layer. |
| `validation.py` — new | Check intermediate response structure, evidence references, final schema rules, and semantic invariants. | Never imports `check.py` or any evaluator. Does not repair meaning by inventing values. |

Keep `run.sh`'s public interface, `schema.json`, and `check.py`. Do not change the schema or checker to accommodate predictions. Tests can use the standard-library test runner and synthetic fixtures. A separate evaluation framework is unnecessary for version 1: after approval, the supplied checker can evaluate frozen outputs as an explicit separate command.

Dependency direction: `solution.py` coordinates the other modules; `tasks.py` may call the task-review function in `reasoning.py`; `reasoning.py` uses `llm.py` and `validation.py`; `data.py` and `validation.py` do not import semantic stages. This avoids circular dependencies. Use ordinary dictionaries and a few small record definitions near their owning module rather than a separate type hierarchy.

Prefer an already available, compatible offline schema dependency over writing a validator unnecessarily. `validation.py` should be a thin adapter around that dependency plus the project's evidence, coverage, date, and task-state checks. Read the actual `schema.json`; do not copy its enums into a second contract. This does not add a seventh application module.

Read-only inspection found local Windows package metadata for `jsonschema` 4.26.0, requiring Python >=3.10 and transitive dependencies including `attrs`, `jsonschema-specifications`, `referencing`, and `rpds-py`. This confirms local metadata presence only: no import was executed, and neither working imports nor availability on the target Linux environment has been verified. The starter allows Python 3.9 or later, so this installed version must not silently raise the submission's minimum Python version or be assumed portable from Windows.

Make one packaging decision before implementing validation: if a compatible, pinned validator and its dependencies are available offline on the chosen supported Linux interpreter, use it and verify it with network disabled. Do not copy platform-specific Windows dependencies into Linux or install from the internet during grading. Verify use of Draft 2020-12 and keep schema resolution local. No format extras are needed for this schema; project date/time checks remain explicit in Python because the supplied schema does not enforce those formats.

Only if that offline dependency cannot be supplied practically, choose a small custom validator for the exact used vocabulary: `type`, `enum`, `required`, `properties`, `additionalProperties`, `items`, `minItems`, `maxItems`, and `oneOf`. Treat title/description/schema-identification fields as metadata and fail clearly on unsupported validation keywords. Test every rule, nullable values, nested objects, and the exactly-one chat target. This is a scoped implementation, not full JSON Schema support. Do not build both validators for production or silently switch when an import fails: record the chosen backend/version, and fail configuration if that backend is unavailable. An already working local dependency can serve as a development reference for synthetic cases if the custom route is chosen, without becoming a runtime dependency.

**2. Exact end-to-end data flow.**

The proposed normal run has the following order. Model stages are bounded batches, not one call per person or message.

| Step | Input → operation → result | Model calls? |
|---|---|---|
| 0 | Arguments/environment → validate configuration, start monotonic deadline, create empty budget ledger → run context. | None; an approved compatibility check can be a separately counted setup job. |
| 1 | `chats.jsonl`, `messages.jsonl`, `seed.json` → validate, preserve raw text/IDs, index, sort → input store and end-of-data time. | None. |
| 2 | Per-chat messages → bounded windows with overlap and explicit primary coverage → extraction-job manifest and initial call/token estimate. | None. |
| 3 | Each window plus relevant seed facts → shared extraction → relationship/organisation observations, goal candidates, task creations, and task-update events. | One request per window/job, plus bounded recovery. |
| 4 | Valid observations → merge overlap duplicates and build compact evidence packets → global observation store. | None. |
| 5a | Organisation observations plus seed names → reconcile actual organisations and aliases → canonical organisation records and IDs. | Batched context-resolution requests. |
| 5b | Person/chat observations plus canonical organisations → resolve circles, links, care relationships, and chat targets → people and chat arrays. | Batched context-resolution requests; direct-chat defaults and seed circles use Python. |
| 5c | Goal observations plus original evidence → merge, reject unsupported intentions, choose allowed categories → at most ten goals. | Batched context-resolution requests; skip only if extraction produced no candidates and coverage succeeded. |
| 6 | Task creations/update events plus resolved people/chat context → same-chat matching, cross-chat review, chronological replay → task ledger with final states. | Batched task-review requests only where interpretation is needed. |
| 7 | Final open tasks plus responsibility/context → assist/remind/leave decisions → help details attached to open tasks. | Batched final-decision requests. Closed tasks require none. |
| 8 | All five results → field allowlist, actual-schema validation, semantic checks, stable sorting → one validated JSON object. | None. |
| 9 | Validated JSON → temporary file beside requested output → final validation and atomic replacement → output file and concise run diagnostics. | None. |

Steps 5a–5c use functions and variants of one context-resolution prompt family, not three separate subsystems. Task-review and help requests share another small prompt family but keep their result types distinct. The shared extraction pass is the only routine pass over all raw messages. Later requests contain compact observations and just the relevant original evidence.

Large decision sets are partitioned by entities or chats. Cross-partition organisation aliases receive a bounded merge review before IDs are finalised. People can legitimately link to several organisations; conflicting profile observations are reviewed rather than letting the last response overwrite earlier facts. A final consistency sweep checks duplicate organisations and conflicting chat targets. No unbounded recursive merging loop is allowed.

**3. Minimal input/evidence contract.**

The loader explicitly opens only the three allowed input filenames. It does not enumerate the input directory, search for JSON files, check whether an answers directory exists, or import `check.py`. Seed facts are allowed input; reference labels are not. Resolve the allowed filenames to regular input files, and reject paths redirected into an answers directory. Inference modules receive parsed records, not an unrestricted dataset-directory handle they can search later.

Retain original message IDs, chat IDs, sender IDs, timestamps, kind, text, and quoted ID. Sort by timestamp with original input position as a stable tie-breaker. A tie-breaker makes processing reproducible; it does not prove a real temporal order between simultaneous events. Set `as_of` to the latest input timestamp. Use a separately documented timezone policy for relative dates; Asia/Kolkata remains an assumption to confirm, not a fact inferred from every message.

A window contains primary messages to extract and a small amount of overlapping context. Every message or span of a very long message has exactly one primary assignment; overlap does not count as additional coverage. Long text is split into spans retaining the same message ID, not cut off silently. Missing replies remain null. Media placeholders provide no attachment contents. Keep English, Hindi, Bengali, and Hinglish in their original form; no whole-dataset translation stage is needed.

Each observation contains its category, subject/entity IDs, source message IDs, a short supporting span where useful, and its proposed meaning. Unknown source IDs and citations outside the supplied/retrieved context are rejected. Keep all provenance locally; final output includes only fields permitted by the real schema. Model instructions must treat chat text as data, including any instructions embedded in a conversation.

There are only two important long-lived derived stores: a compact context store for people/organisations/chats/goals, and a task ledger. Keep request counters, coverage states, and validation errors in a small run record. No database or persistent cache is needed.

**4. All five categories in the first version.**

| Category | Minimum real implementation |
|---|---|
| People | Start from all non-`ME` participants, preserve supplied seed circles, aggregate evidence across chats, choose one allowed circle, and produce supported organisation/care links. |
| Organisations | Discover entities the user runs/belongs to; combine supported aliases/chats/people; infer required type/side/role; do not create an organisation for every group or client company. |
| Chats | Assign every chat exactly once. Use the other participant as a direct-chat default where appropriate; infer group purpose and allow group-to-person assignments. |
| Goals | Distinguish the user's supported habits, milestones, and experiences from ordinary tasks/forwarded content; merge duplicates; choose area/type/horizon and real evidence; output no more than ten. |
| Open loops | Extract obligations/questions, resolve owners, reconcile updates, preserve done/dropped tasks and closure evidence, and choose help for final open tasks. |

The schema has no unknown circle or unknown chat target. For uncertainty, request the best-supported allowed decision with an internal low-support flag and, if budget permits, one focused review. Do not confuse a model's forced choice with a verified fact. If no defensible required record can be produced after failures, the run is incomplete; do not invent an organisation or treat a blanket friend assignment as a successfully inferred result. Optional unsupported links/goals are omitted with diagnostics. Any emergency fallback would need to be explicit and would not pass the normal completion gate.

For help, retain all three choices. `assist` includes a useful proposed step and whether that step needs permission; `remind` includes a time based on evidence and a documented timing policy; `leave` explains why intervention is unsuitable. Closed loops have no help object. The program writes recommendations, not external actions. Use null for unjustified due dates. A reminder-time policy is not a claimed conversation fact.

**4a. Deterministic selection of at most ten goals.**

The LLM interprets candidate meaning and proposes supporting messages. Python performs eligibility checks, calculates a ranking key from validated evidence, and takes the first ten. Selection is deterministic for the same validated candidate/evidence records; this does not claim that fresh LLM extraction itself is deterministic.

First require an actual goal rather than only an immediate task, evidence that the user owns/adopts the intention or practice, at least one existing supporting message ID, and valid area/type/horizon fields. A seed goal without message evidence is context only. Reject forwarded promotions, unsupported other-person goals, and guesses with reason codes. Candidates awaiting a failed review are pending, not rejected. Unresolved semantic uncertainty that has actually been reviewed can be rejected for insufficient evidence, with its sources retained in diagnostics.

Merge candidates representing the same intention/outcome before ranking. Do not merge by area alone, and do not treat shared evidence IDs as sufficient proof of equivalence. Retain the union of genuine supporting evidence for each merged goal. Exact duplicate observations from overlap are counted once. Repeated copies, quotations, or forwards of one utterance do not create independent support. A concise original supporting span is used for deduplication; raw text and original IDs remain intact.

Assign one evidence tier, using the strongest validated support:

| Tier | Required evidence |
|---|---|
| 3 — Explicit intention | An original `ME` message states or clearly reaffirms a goal, intention, target, or ongoing habit. An explicit adoption in reply counts only when the antecedent establishing the goal is cited too. |
| 2 — Observed sustained pursuit | No tier-3 statement, but original `ME` messages on at least two distinct dates support concrete pursuit of the same broader outcome/practice. The wording must support the goal, not merely two unrelated errands. |
| 1 — Indirect but corroborated | No higher-tier evidence, but at least two distinct non-duplicate conversational episodes attribute the goal to the user, and an original `ME` message in the evidence corroborates ownership. Third-party assertions alone are insufficient. |

Candidates meeting none of these tiers are excluded as insufficiently supported; this is a conservative design policy, not an organiser rule. Important one-off explicit aspirations qualify at tier 3. A seed statement alone does not boost a goal's rank or supply missing evidence.

For eligible, deduplicated candidates sort by this exact sequence:

1. Evidence tier, descending.
2. Number of distinct dates containing independent positive `ME` support for this goal, capped at three, descending. The cap limits the advantage of frequently repeated work chatter. Use the same configured timezone policy throughout the run and test date-boundary behavior.
3. Timestamp of the latest original `ME` message positively supporting the goal, descending. A reminder from somebody else, a copied forward, a rejection, or a mere mention does not refresh this value.
4. Timestamp of the earliest supporting message, ascending.
5. Sorted unique supporting message IDs, compared lexicographically as strings, ascending.
6. A stable internal candidate key: earliest primary source span, canonical area/type/horizon, then Unicode-normalised title, ascending. No random UUID or API completion order enters this key.

Take the first min(10, eligible goal count), preserving that order in output. A tie remaining after all fields means equivalent stored candidates should already have merged; reject duplicate internal keys instead of selecting by arrival order. Do not impose area quotas, invent importance scores, use model confidence as a probability, or add irrelevant evidence to inflate rank. Store the ranking components and rejection reasons internally, not as extra final-output fields. Output the genuine supporting evidence IDs, with both sides of any adoption exchange, rather than the whole conversation.

This policy prioritises evidential strength, repeated user support, and recency; it does not claim to know the user's true ranking of life priorities. Normal goal eligibility is not restricted to unfinished goals: a supported goal appearing in the history is not removed simply because a milestone was achieved. Original goal evidence and later changes remain available for accurate wording.

Minimum selection tests: more than ten eligible candidates select exactly the expected ten; fewer than ten are not padded; a one-off explicit goal outranks weaker repetition; duplicate windows/forwarded copies cannot improve rank; permutation of candidate/API-return order cannot change selection; exact ties use the declared stable fields; invalid/unsupported candidates are excluded with reasons; distinct goals in the same area remain separate; adoption cites both original messages.

**4b. Empty results versus incomplete inference.**

Maintain stage state independently of the output arrays. Use `not_started`, `running`, `succeeded`, `succeeded_empty`, `failed`, or `incomplete`. A caught exception must never be translated directly into `[]`. Store required/completed job IDs, primary coverage, proposed/resolved/rejected/pending candidate counts, failure reasons, and semantic uncertainty flags in the run record. Derive each category's state from all its prerequisite stages, not merely its final model response.

`succeeded_empty` means every prerequisite and required primary window completed, every proposed candidate received a valid disposition, and no supported final items remain. It means no supported findings from completed inference, not mathematical proof that no true items exist. `failed` means an unrecovered operational/configuration/validation failure prevented the required result. `incomplete` means some required coverage or decisions remain pending, including time/token cutoff, unresolved malformed output, or skipped candidate-search work. Preserve valid partial work without relabelling the stage as success.

| Category | Conditions allowing a genuinely completed empty result |
|---|---|
| People | The validated input has no non-`ME` people to represent. A nonempty person registry with no classifications is failed/incomplete, not empty. |
| Chats | The validated input has no chats. Otherwise every chat needs exactly one target, including chats with no messages. |
| Organisations | Organisation discovery and seed/name consideration completed, no supported organisation survives, and all chats/person references can be resolved without an organisation. A failed organisation call is not evidence of no organisations. |
| Goals | Extraction coverage succeeded and all candidates were either validly rejected/deduplicated or none were found. A missing goal-classification response leaves pending candidates. |
| Open loops | Task discovery and event review completed with no supported obligations. All tasks being done/dropped does not make this array empty: those tasks remain in it. Unprocessed origin/update events block a completed-empty claim. |
| Help substage | If task reconciliation succeeded and there are no final open loops, record `succeeded_empty` with reason `no_open_loops`; closed loops remain in the loop output. If open loops exist, every one needs a valid help decision. |

Distinguish an evidence-based unresolved interpretation from an unprocessed job. For example, after every planned relevant candidate was reviewed, a genuinely ambiguous update may receive the explicit disposition `ambiguous_evidence`, leaving the task's last supported state and a quality flag. That is a completed conservative decision, not a transport failure. If matching stopped before reviewing the required candidate set, it is incomplete. Track these separately so successful execution cannot hide processing gaps or pretend all meaning is certain.

Overall success requires each required category/substage to be `succeeded` or `succeeded_empty`, complete mandatory coverage, no pending required decisions, and successful final validation. Add no status fields to the challenge JSON. Emit the run status and counts separately through diagnostics. On failure/incompletion return a non-success outcome and do not replace the designated final output. Optional partial artifacts, if enabled later, use a distinct explicitly marked path. An old output file is not evidence of a successful new run; report the current run ID and outcome.

Minimum status tests: a truly empty synthetic input; nonempty people/chats with missing results; completed extraction with no goals; all goal candidates validly rejected; extraction timeout that returns no records; an omitted entity in otherwise valid JSON; all loops closed; open loops missing help; a reviewed ambiguous update versus a budget-stopped candidate search. The expected stage state and overall exit outcome must be asserted, not just the final array length.

**5. How task extraction and identity work.**

Use a small internal task record: internal task ID; original source/chat; canonical action and object; current owner; owner evidence; due date/evidence; ordered event list; current status; current closure ID; and supporting source IDs. Model-generated internal names are replaced with deterministic IDs by Python. Internal event types can include create, acknowledge, update, complete, cancel, and reopen; these are not extra output status values.

Extraction returns both new obligations and update observations. It can say an update has an unresolved target. This matters when an isolated message says a document was sent but the original promise is in another window. Never discard an update merely because its origin is absent locally. Conversely, a bare completion remark must not manufacture an earlier promise without evidence.

One message can create multiple obligations. Split genuinely separate actions or owners into distinct candidates. Two observations from overlapping windows are duplicates only when source/span and task meaning agree; the shared message ID alone is not a deduplication key. Keep multiple evidence messages for one task without emitting a separate task for every reminder.

The canonical `source_msg` is the message that actually raised the obligation or unresolved decision. Do not replace it with the latest reminder or search reference answers for a better-scoring source. When a task is merged across chats, preserve a stable origin and its chat. Keep other originating/supporting messages internally. Final status is determined using all supplied later evidence, including earlier contextual weeks of hidden input.

**6. Ownership, matching, and cross-chat updates.**

Ownership means who owes the action, not who wrote the message. A first-person promise generally belongs to its speaker; a request requires identifying its addressee; a followup can be owned by the person who owes delivery to the user. Sender IDs resolve identity, while the model interprets pronouns, delegation, and plural language. Do not assign every group request to `ME`. If two owners owe separable actions, split the tasks; if a genuinely shared action has no identifiable accountable owner, retain uncertainty and review instead of inventing a person.

For every task event, generate candidate task IDs using this sequence:

1. Look for a quoted/source reference or a concrete shared identifier such as the same document/project reference. A reply link retrieves candidates; it does not prove that every task in the quoted message was completed.
2. Search tasks from the same chat using action/object, participants, owner evidence, and chronological context. Include closed tasks because an update can reopen them.
3. For still-unresolved events, search other chats using a shared person plus a specific object/reference or another explicit linking statement. The mere presence of `ME` in both chats is not a useful cross-chat cue.
4. Batch ambiguous event/candidate sets into a model request containing the original origin and update texts. The response must assign each event to a candidate task, identify a supported new task, or explicitly leave the link unresolved. It must cite the event and supporting evidence.
5. Validate IDs and scope, apply accepted links, and replay each affected task's events in chronological order. The model chooses a semantic operation; Python controls state and preserves history.

Start with small candidate packets. If a packet is too large, partition candidate IDs and retain the full candidate list locally. When no supported match is found in the first packet, expand to the remaining relevant candidates subject to budget. Do not report a truncated candidate search as exhaustive. Lexical matching finds candidates; it cannot by itself establish completion or handle every multilingual paraphrase. Cross-chat recall without explicit linking cues remains a known version-1 limitation, not a reason to merge loosely related work.

Match batches may run concurrently only when they do not share task state. Process events affecting the same task sequentially, or collect proposed links independently and replay all accepted events afterward. Deterministic merge order prevents whichever API call finishes first from deciding task identity.

**7. Completion, cancellation, and reopening rules.**

| Existing state + supported event | Result | Evidence rule |
|---|---|---|
| No task + an established obligation | Open task | Record original source and owner evidence. |
| Open + acknowledgement, progress, or revised due date | Remains open | Preserve the update; do not assign closure. |
| Open + fulfilled obligation | Done | `closed_by` points to the message establishing fulfilment of this task's scope. |
| Open + explicit cancellation or abandonment | Dropped | `closed_by` points to the cancelling message. |
| Done/dropped + explicit renewal of the same obligation | Open | Add reopening event and clear the current `closed_by`; retain the old closure in internal history. |
| Done + a genuinely different deliverable | Original remains done; create related new task | New source belongs to the new obligation. Similar subject matter alone does not require reopening. |
| Any state + ambiguous/unmatched update | Preserve the last supported state | Keep an unresolved event; do not guess closure. |

Silence, a passed deadline, a checkmark without clear context, or an okay is not automatic completion. Cancellation under negation must not drop a task. Completion applies to the obligation's actual scope: sending proof and receiving payment are different milestones. One completed subtask must not close a larger compound obligation. Reassignment updates the owner only when supported; it does not itself close the task.

Cross-chat closure is allowed when linked by evidence. `source_msg` must belong to the loop's declared origin chat, but `closed_by` may belong to another chat. Evidence predating the origin cannot normally close that later obligation; handle contradictory timestamps as uncertainty rather than forcing an order. After a late cross-chat match, replay affected history so a late-discovered earlier completion does not overwrite a subsequent reopening.

Synthetic walkthrough, not development data: in chat A, a person promises to send a draft; another participant says okay; in chat B, the same sender explicitly says that draft was sent; later, the requester says the same promised draft still needs the agreed corrections. The first message creates a task; okay only acknowledges it; the explicit cross-chat reference can justify completion; the later clarification can reopen it. If instead the requester asks for a separate new report, create a new task. The model resolves that distinction from the exact wording, not a universal keyword rule.

**8. API-call and token-budget mechanism.**

Keep one small budget record in the orchestrator and let every HTTP attempt reserve against it. Track calls completed, calls in flight, estimated and reported input/output tokens, time remaining, recovery attempts, and work still required per stage. No stage may call the API outside this path. Stage budgets are accounting entries, not new modules.

There are three prompt families: extract evidence, resolve context, and decide task operations/help. Separate job types within those families make the number of calls visible:

| Count symbol | Jobs counted |
|---|---|
| E | Extraction windows, packed from actual messages. |
| O | Organisation-resolution batches, including necessary cross-partition merge work. |
| P | People/chat-resolution batches. |
| G | Goal-resolution batches. |
| M | Same-chat task-matching batches. |
| X | Cross-chat or unresolved-event review batches. |
| H | Final help-decision batches for open tasks. |
| Q | Any approved compatibility/setup calls. |
| R | Extra retry, repair, or split requests actually sent. |

Base call count = E + O + P + G + M + X + H + Q. Total calls = base calls + R. There is no term for a mandatory call per message, person, or task. Jobs are packed until their full request and reserved response fit the configured limits. A stage with no supported candidates needs no model call, but failed extraction must not masquerade as no candidates.

Before the first request, E is known exactly from the window manifest. Downstream counts are provisional because task density and model output are unknown. Use a short initial tranche of real extraction jobs after execution is approved, count their output observations and tokens, and project a range for the remaining jobs. Those initial results are reused, not discarded benchmark calls. Update projections as each stage's actual candidate list becomes available. Report counts as measured, planned, or projected; do not pretend all downstream work was known before extraction.

For a request j, estimate input tokens from the entire serialized message payload, including instructions, schemas, seed facts, IDs, timestamps, overlap, retrieved context, and any repair transcript. Reserve an output allowance separately. If a verified compatible tokenizer is available locally, use it. Otherwise use a clearly labelled conservative text/UTF-8-size proxy and calibrate it against reported prompt usage from actual calls. Do not assume a universal four-characters-per-token conversion, especially for mixed scripts. A byte-based proxy is an estimate, not a guaranteed bound for an unknown API tokenizer.

Maintain a safety factor from observed estimate-to-usage discrepancies, increasing it when the estimator undercounts. Keep the verified endpoint context/output limits as configuration; if those limits are unknown, disclose that exact fit cannot be guaranteed and verify them before a full run. Do not invent a context size from an OpenAI-compatible label. Provider-reported usage is authoritative for observed consumption; absent usage remains unknown and retains a conservative reservation.

Planned token reserve = sum of estimated input tokens plus reserved output tokens for queued jobs, plus a separately visible recovery reserve. Actual reported tokens, unknown-usage reservations, and outstanding reservations must together stay within the configured run token ceiling. Reserve before dispatch to prevent concurrent calls from overspending the same remaining balance. An output cap is not proof that the answer will be complete; truncation is handled explicitly below.

The spending ceiling and token ceiling must be configured from the user's approved budget and verified provider pricing. If prices are not supplied, report tokens and leave dollar cost unknown. If rates are supplied, estimate cost by multiplying each billed token category by its corresponding verified rate; do not double-count reasoning tokens already included in completion tokens. No example dollar price or measured cost is asserted by this plan.

Proposed starting recovery policy: reserve up to 20% of planned base calls for extra requests, with one shared cap across retries, repair, and splitting. Each original job may generate at most three outbound transmissions in total, including its split children. This prevents a retry tree from growing exponentially. These are configurable engineering starting values, not provider limits. If a failed original call is split into two children, those three transmissions exhaust that job's allowance; the children do not each receive fresh retry budgets.

**9. Planning for the 30-minute limit.**

Use a monotonic clock for elapsed runtime, independent of message timestamps. Proposed schedule: all model I/O must finish by minute 27; target process exit by minute 29:30, leaving 30 seconds before the external limit. These are time allocations, not claims that the work fits. Successful full coverage must be demonstrated later on a cold run.

Estimate each stage using its actual/forecast job count N, conservative observed request latency L, concurrency c, and any verified requests-per-minute or tokens-per-minute limits. A useful planning expression is:

Stage time estimate = the largest of request-wave time, rate-limit time, and the longest dependent request chain, plus backoff allowance.

Request-wave time is approximately ceil(N / c) × L. Request-rate time is 60 × N / allowed requests per minute. Token-rate time is 60 × planned tokens / allowed tokens per minute. Use the provider's actual accounting definition if input/output quotas differ. Dependent task updates cannot be accelerated merely by increasing c. Add stage estimates at dependency barriers and include local processing, recovery, and export reserves. This is a forecast, not a hard proof; small latency samples are especially uncertain.

If quota limits are unknown, do not assume unlimited throughput. Use measured successful throughput and retain an explicit unknown-rate-limit warning in the run diagnostics. Start with one in-flight request; permit small bounded concurrency only after endpoint tests and the forecast show it is necessary and safe. Even with concurrency, completed responses are merged in stable job order.

Before dispatching every request, check the remaining token reservation, remaining recovery allowance, request deadline, and estimated mandatory downstream work. Reforecast after each batch. If the forecast no longer fits, first remove optional second opinions and duplicate context, then repack only within verified context/output limits. Do not silently discard input messages, final reconciliation, or all goals/help to meet the clock. If essential work still cannot fit, mark the run infeasible/incomplete and report which work remains.

A socket timeout alone is not a reliable total wall-clock deadline. `llm.py` should run blocking HTTP in a small worker process controlled by the parent. Start with one worker. The parent sets an absolute per-attempt deadline, requests termination, waits only a bounded grace interval, escalates to a forceful kill if necessary, and reaps the child with a bounded wait. It must also close its communication handles and avoid waiting on a blocked queue feeder at shutdown. Threads with a timeout on waiting alone would not provide that guarantee. Section 9a specifies how to test this rather than assuming it works.

Use per-attempt timeout no greater than the remaining network allowance. Reject new calls that cannot reasonably finish with their downstream reserve intact. At the network cutoff, terminate in-flight work, preserve already validated results, and finish local diagnostics. Publish the designated final output only on overall success as defined in section 4b. Optional partial output uses a separate marked path and a non-success outcome; never replace the designated final file with partial results. Existing final output must not be mistaken for a new successful run after failure.

The preflight/run summary should report planned versus actual calls per job type, estimated versus reported tokens, unknown usage, latency samples, retries/splits, covered versus failed primary messages, unresolved events, time reserved for downstream work, validation outcome, and completion state. No API secrets or raw private message text belongs in routine diagnostics. These counters are essential; a dashboard and persistent cache are not.

**9a. Practical local tests and mandatory Linux deadline tests.**

Keep ordinary local tests fast: inject a fake clock and fake transport, advance time without sleeping for 30 minutes, and assert dispatch decisions, recovery limits, stage states, and cleanup requests. Use a spawn-based process test with a synthetic worker to exercise real child creation/termination on Windows as well. Local Windows success does not establish Linux signal, process-group, shell, or packaging behavior.

For Linux, use a clean Linux container or VM with the submission's selected supported Python version and offline dependency bundle. WSL can be convenient for development, but the acceptance record must identify the actual Linux distribution, interpreter, process start method, and launcher used. No such environment test has run yet. Prepare any test image/dependencies before the offline test; disable external networking and use fake transports. Optional loopback-only slow-server fixtures need no model endpoint, credentials, or challenge data.

The application deadline covers normal orchestration and HTTP children. To protect against a hung parent, final validation, or serialization, require a launcher-level hard timeout too. Proposed minimal Linux choice: verify a suitable `timeout` utility on the target, then make a small approved future `run.sh` integration that starts the timeout before Python startup, sends termination at 1,770 seconds, and forcefully stops remaining run processes after a two-second grace. Keep workers in the run's process group and prohibit detached children. The public two-argument interface and six Python modules remain unchanged. Do not assume the utility exists or its process-group behavior works: the target test must prove both. If unavailable, Linux readiness fails until an equivalent supervisor is selected and tested; silently omitting this safeguard is not acceptable.

Use shortened real-time deadlines for integration tests, for example: six-second network cutoff, ten-second application exit target, twelve-second outer termination, one-second force-kill grace, and a separate test-harness emergency timeout at twenty seconds. These are proposed test settings, not measured performance. The harness observes wall time independently of the clock being tested. An overloaded host that violates timing tolerance yields a failed/inconclusive test to investigate, not permission to widen limits until the test passes.

Required Linux scenarios are: worker hangs before receiving any body; worker produces slow partial data; worker stalls while transferring its response; retry delay extends past cutoff; child exits/crashes without a valid result; child ignores normal termination so force-kill is exercised; and the main process hangs so the outer launcher must terminate the entire run. Also exercise a normal successful run through the same launcher and an interruption during temporary-file writing.

Record run-owned PIDs/process-group IDs, dispatch/termination/reap timestamps, exit outcomes, stage states, and output hashes. Pass only when: no dispatch occurs after cutoff; the worker is reaped within the configured grace plus a declared small scheduling tolerance; no run-owned child remains alive or unreaped; the outer hang case exits no later than outer deadline plus kill grace plus that tolerance and strictly before the harness emergency timeout; forced termination is non-success; and an existing final output remains byte-for-byte unchanged on all incomplete runs. For a proposed two-second test scheduling tolerance, the example outer case must finish by fifteen seconds. This is an acceptance bound to test, not an assertion about the environment.

Test the production constants as configuration values as well: network cutoff 1,620 seconds, application/launcher termination target 1,770 seconds, force-kill grace two seconds, and total allowance below 1,800 seconds including a documented startup/cleanup margin. The final measured full run remains the scaling check after paid-run authorization; accelerated failure tests prove shutdown mechanics without spending half an hour per local test. Handle output validation and export inside the overall deadline, not as unbounded work after it.

**10. Failed, incomplete, or malformed responses.**

All responses are proposals until validated. Apply the checks in this order: transport outcome; usable/non-refused content; truncation metadata when available; JSON parsing; expected stage fields/types; required item IDs and batch completeness; valid evidence references; semantic consistency. Metadata availability is provider-specific and must be verified. A normal finish indicator does not prove factual completeness.

| Failure | First-version behavior |
|---|---|
| Temporary timeout, rate limit, or server error | Retry within the job/global recovery and deadline allowances. Respect a supplied retry delay only if it still fits. Bound all backoff. |
| Invalid credentials or permanent configuration error | Fail promptly. Do not burn the recovery budget repeating the same invalid request. |
| Unsupported optional request parameter | Allow a single documented capability correction if verified; otherwise fail configuration. Never silently change the model or endpoint. |
| Empty reply or explicit refusal | Treat the job as failed. At most one appropriately narrower/rephrased attempt within the same caps; repeated refusal is not success or no findings. |
| Malformed JSON or wrong types | One repair request with the exact errors and necessary original context if budget permits. Do not use unrestricted text evaluation or guess missing JSON fragments. |
| Output truncated | Discard the incomplete structure and split the original job once into smaller primary ranges/candidate groups, preserving overlap and references. Both children share the original transmission cap. |
| Valid JSON missing requested people/chats/decision IDs | Preserve independently valid items in memory, request only missing items within budget, and keep the parent job incomplete until required coverage is satisfied. |
| Invented IDs, unsupported citations, impossible owner | Reject affected records. A valid JSON object does not make its evidence real. |
| Conflicting completion/ownership decisions | Retrieve the original evidence for a bounded review; if unresolved, retain the last supported task state rather than guessing closure. |
| Recovery/deadline exhausted | Record failed coverage/unresolved decisions, finish local validation, and report an incomplete run. Never replace the failure with an apparently successful empty category. |

Require an acknowledgement of the primary message range or requested entity/event IDs in intermediate results so omissions can be detected. This verifies structural coverage, not semantic recall: an LLM can acknowledge a message and still miss a task. Manual review is needed to measure that error. If a response claims an internal output limit was reached, split the job even if its JSON parses.

Cache only complete validated results in a run-local dictionary keyed by exact request content, stage/schema version, endpoint/model/settings, and relevant context. A corrected seed fact or changed task state must produce a different key. No disk cache or resume framework is needed in version 1. A timeout may have incurred remote billing even if usage was not returned; log it as unknown, not free.

**11. Minimum tests and acceptance criteria by implementation stage.**

These are future tests after approval; none were written or run during planning. Use synthetic messages and a fake HTTP transport/clock first. Deterministic tests validate the code's mechanics. They do not establish real model accuracy. A later small live sample assesses language interpretation, followed by a cold-run rehearsal. Do not require repeated full development runs to test ordinary formatting logic.

| Stage | Minimum tests | Acceptance gate |
|---|---|---|
| A. Input and evidence (`data.py`) | Mixed-script UTF-8; shuffled messages/timestamp ties; blank lines; conflicting duplicate IDs; unknown chat/sender references; missing reply; media placeholder; long-message spans; zero-message chat. | Every primary message/span is covered once, raw IDs/text preserved, sorting stable, and invalid structural input reported rather than silently lost. |
| B. No-answer boundary | Synthetic directory containing a decoy answers path; intercept file opens and forbid directory scans; compare runs with/without decoy files using fixed model responses. | Only the three allowed data files are read; no inference import of `check.py`; identical allowed inputs produce identical request payloads and outputs regardless of decoys. No real answer key is needed for this test. |
| C. Validation/export (`validation.py`, `solution.py`) | One valid fixture exercising all five categories; negative cases for every used schema rule; unknown/nested extra fields; both/neither chat targets; invalid references; eleven goals; missing evidence; help on a closed loop; missing action-specific fields; invalid dates; interrupted write; offline availability of the single backend selected in section 1. | All deliberately invalid cases are rejected; the valid fixture passes actual-schema and semantic checks; interrupted writes never publish partial JSON. If the scoped custom backend is selected, unsupported validation keywords fail explicitly. No silent backend switch is permitted. |
| D. Client and budget (`llm.py`) | Successful/empty/malformed/truncated responses; temporary error then success; persistent/auth failure; hung worker; missing usage; exact-request deduplication; changed-context cache miss; insufficient token/time budget. | Attempts, split children, waits, and in-flight reservations obey caps; a hung worker is terminated; unknown usage is retained; no calls are sent after cutoff; no API key is logged. |
| E. Shared extraction and context (`reasoning.py`) | Mocked windows with overlap; unknown cited ID; partial entity batch; one person across two chats; one organisation across groups; two organisations sharing a participant; group assigned to a child; user goal versus forwarded promotion; all goal-selection cases in section 4a. | Duplicated observations merge without losing provenance; seed circles persist; real inference paths exist for people/organisations/chats/goals; every required chat/person is accounted for; deterministic ranking selects no more than ten supported goals. |
| F. Task ledger (`tasks.py`) | Promise→acknowledgement→completion; cancellation versus negation; completion→reopening; distinct new task after completion; reassigned owner; two tasks from one message; same task in overlapping windows; ambiguous short reply; explicit cross-chat completion; unrelated similar task in another chat. | Fixed accepted event fixtures yield exactly expected owners/statuses/origins; no false closure from acknowledgement; reopened tasks clear current closure; unrelated tasks remain separate; cross-chat evidence is preserved; replay order is stable. |
| G. Help and integration | Open tasks requiring assist/remind/leave; step-specific permission flag; closed task with stale help; due-date ambiguity; failed stage; identical mocked run twice; deterministic name-renaming fixture; all stage-state cases in section 4b. | All open tasks have complete valid help decisions in successful fixtures; closed tasks have none; outputs use only schema fields; failures are distinguishable from completed-empty results; incomplete runs do not publish the designated final file; deterministic replay produces identical JSON. |
| H1. Readiness before paid full-dataset execution | Linux offline packaging and all section 9a deadline cases; a representative-volume synthetic run using fake responses; a separately authorized bounded live pilot; the input-only work estimate and section 11a approval checklist. | All section 11a gates pass and the user explicitly approves the concrete full-run scope and spending limit. No paid full-dataset run is needed to pass its own authorization gate. |
| H2. Authorized full-dataset rehearsal | After H1 and approval: actual input-only cold run on Linux, no prefilled cache, only the configured model endpoint reachable. | Actual measured runtime is below 30 minutes, output is valid, mandatory coverage/stages are complete, and usage or unknown usage is reported honestly. Failure blocks claims of submission readiness; it does not retrospectively justify another paid run without budget authority. |

Stage F tests should supply accepted semantic decisions to test state transitions independently of an LLM. Separately ask the live model to interpret a few synthetic wording variants after approval. That distinction shows whether a failure is in language interpretation or in Python state handling.

The first successful full version must have all five category paths, all chats and relevant people represented, no invalid references, complete successful primary coverage, bounded network work, and explicit low-support/unresolved diagnostics. Schema compliance is not an accuracy score. Do not declare completion if source messages were skipped or required stages failed.

Future development scoring stays outside inference: freeze output, then invoke the unchanged checker separately after approval. Goals/help require manual review because the supplied dev labels do not cover them. Review both predicted items and independent conversation windows to find false positives and false negatives; unmatched predictions can also reflect incomplete reference labels. No reference-derived person mapping, acceptable-source list, or help decision is copied into inference prompts or caches.

**11a. Minimum gate before authorising a paid full-dataset run.**

Passing tests makes the implementation ready to propose a paid run; it is not permission to spend. Planning approval, implementation approval, a small pilot's spending approval, and approval of a full-dataset run are separate scopes unless the user explicitly combines them. None is granted by this document. All checks below are future work; no test, API call, or solution run has been performed during this clarification.

Require every gate below before requesting authorization for a paid full-dataset run:

| Gate | Minimum evidence to present |
|---|---|
| 1. All category paths and evidence protections work | Stages A–G pass with synthetic fixtures, including nonempty valid results for all five categories, all three help actions, seed preservation, evidence-reference checks, deterministic goal selection from more than ten candidates, and the task-state/ownership/cross-chat cases. A valid output full of unexplained empty arrays is not sufficient. |
| 2. Failure is not reported as empty success | The section 4b cases pass. Incomplete/failed stages produce non-success and cannot replace the designated output. Reviewed semantic ambiguity and unprocessed work have different diagnostics. Old output hashes remain unchanged in failure tests. |
| 3. Answer isolation is demonstrated | Synthetic decoy-answer tests and file-open instrumentation show only the three allowed dataset files are read. Changing or removing the decoy has no effect on inference requests/results. No real development answer files are needed for readiness testing, pilot selection, or inference. |
| 4. Offline Linux validation and cleanup work | The selected validator and dependencies work offline on the recorded supported interpreter. All section 9a process/launcher tests pass, including the ignored-termination and hung-parent cases, with no remaining run-owned children. Local Windows results alone cannot satisfy this gate. |
| 5. Local scale and bookkeeping are exercised without model spend | An offline run using deterministic fake responses and a synthetic dataset representative of the expected message count exercises window coverage, batching, event replay, output size, memory, and export. Include one large chat and long messages, not just many tiny chats. Record actual local elapsed time and memory observations. This checks local overhead and shutdown behavior, not live model latency or quality. |
| 6. A bounded live pilot is separately approved and reviewed | With a specific small spending/call cap, use the intended endpoint/model and the same code, prompt versions, and response schemas planned for the full run. Obtain at least one valid response for each request family, exercise every output category across the chosen cases, and record observed usage, latency, repair behavior, and available response metadata. Reuse qualifying recent pilot evidence only if the relevant build/configuration is unchanged. |
| 7. The pilot's critical semantic checks pass | Predeclare a small review set covering English, Hindi, Bengali, Hinglish, and the critical patterns: acknowledgement without closure, cancellation under negation, completion/reopening, ownership, explicit cross-chat matching, and unsupported goals/help. Cases may be synthetic where the available input lacks a language/pattern. Manually inspect the raw supporting messages and outputs. Resolve observed fabricated evidence, false closure on the declared cases, missing required category handling, and ignored input before scaling. Document other errors and uncertainty; do not invent an overall accuracy threshold or claim hidden-set performance from this small set. |
| 8. A concrete full-run budget and time forecast fit | Perform input-only planning for the intended dataset: count actual windows and use pilot observation density/usage/latency to estimate downstream job ranges. Include retries, output allowances, cross-chat review, all five categories, and finalization reserves. Show a conservative upper planning estimate using the slower/larger observed cases and an explicit safety allowance, not just an average. The planned model work must fit before the 27-minute network cutoff, with the section 9a exit margin intact. If evidence is too sparse or the forecast exceeds time/token/spend limits, do not scale yet. |
| 9. The user approves the specific run | Present the exact dataset path/count, model and endpoint identity without secrets, code/configuration/prompt versions, estimated call/token ranges, verified pricing or other enforceable spend controls, maximum authorized spend, hard call/token/time limits, expected output path, and known pilot weaknesses. Obtain explicit full-run approval or point to an existing approval that clearly covers this exact scope and budget. |

The live pilot itself must not start without its own approved cap. Prefer synthetic cases first; any use of development messages must be limited to allowed inputs and the configured endpoint. No cached answer labels, manual-review labels, or benchmark findings are supplied as inference facts. The pilot is intended to verify compatibility and identify obvious failures cheaply, not to become a disguised full-dataset run.

If returned token usage is absent, do not report a measured token cost. A paid full run can proceed only if its approved maximum spend is still enforceable using verified provider billing/limits or conservative request/output reservations backed by known pricing. Otherwise this gate fails until the uncertainty is resolved. Missing prices must not be replaced with a hypothetical dollar figure. Unknown account quotas and too few latency samples weaken the runtime forecast; disclose them and use a smaller additional approved pilot when necessary.

Keep one concise readiness record with pass/fail evidence for gates 1–8 and the user's gate-9 authorization. This can be part of the existing run documentation; it needs no extra application module or dashboard. Do not require a successful full paid run before requesting its first authorization: that would be circular. The authorized full run is H2 and supplies the actual end-to-end cost/runtime/coverage evidence for later submission readiness. It may still fail under new workload or service behavior, in which case preserve diagnostics, stop within limits, and do not automatically purchase a rerun.

Minimum acceptance-gate tests use recorded/mock readiness results: a missing goal-ranking test, failed Linux cleanup, unresolved mandatory stage, absent pilot authority, over-budget projection, or missing full-run approval must each prevent a full-run-ready decision. A fully satisfied synthetic checklist should produce readiness-to-request-approval only until explicit budget authority exists. These tests verify the gate's mechanics; they do not fabricate passed real-world tests.

**12. Essential version 1 versus optional improvements.**

| Essential first version | Defer until a measured need appears |
|---|---|
| Six modules and the existing two-argument entry point. | A package hierarchy with a separate module for every small responsibility. |
| All five output categories and help decisions. | Multiple models, providers, or independent agents. |
| Raw evidence IDs, full primary coverage, compact context, chronological task ledger. | Vector databases, embedding models, and database persistence. |
| Same-chat matching and evidence-triggered cross-chat matching. | Broad semantic cross-chat search with embeddings. |
| Bounded retries/repair/splitting, one network boundary, hard request deadlines. | Resume/checkpoint infrastructure and provider-specific batch services. |
| Run-local identical-request reuse and usage/time counters. | Persistent result caches, provider-prefix cache optimisation, and dashboards. |
| One selected offline validator backend plus project semantic checks, following section 1. | Parallel production validator implementations or automatic runtime backend switching. |
| Original-language processing and selected raw-evidence retrieval. | Whole-history translation and additional language-detection services. |
| Synthetic regression tests, Linux deadline tests, a bounded approved pilot, and an explicit paid-full-run gate; measured cold-run readiness after approval. | Large automated model leaderboards or repeated full-run tuning without a specific hypothesis. |

The practical implementation order is A/B input isolation → C validation/export → D client/budgets → E extraction/context → F task ledger → G help/integration → H1 readiness and full-run approval → H2 authorized full-dataset rehearsal. That order makes errors observable before complex reasoning is added. A small skeleton run with mocked replies precedes paid testing; a separately approved bounded pilot precedes the full-run authorization decision.

**13. Decisions still needed and explicit limitations.**

- Model/endpoint identity, supported parameters, context/output limits, account quotas, and pricing must be verified before a full paid run. This revision recommends no model as proven best and repeats no unverified capability claims.
- The user's approved testing budget and a corresponding token ceiling are still needed before paid testing. This does not block designing or later testing pure Python with mocks after implementation approval.
- Relative-date timezone and reminder scheduling remain documented policies to agree. No current date is substituted for the dataset endpoint.
- The exact cost-to-points rubric remains unknown. Optimise measured tokens/time and semantic quality, not an invented score formula.
- Lexical/evidence-triggered cross-chat matching can miss implicit paraphrases. Track unresolved events and review a sample before adding more retrieval infrastructure.
- No method can recover attachment contents absent from the inputs. Weak evidence and forced schema categories remain real uncertainty.
- A provider outage or an input exceeding measured capacity can prevent complete inference within 30 minutes. The design bounds execution and reports failure; it cannot guarantee accurate full output under arbitrary service failure.

This is the revised implementation plan for review. It simplifies the earlier architecture without removing any required output category or evidence protections. The earlier architecture report remains an unchanged record; this separate document is the proposed first-version implementation scope. Implementation, solution execution, API calls, and answer-based evaluation await approval.
