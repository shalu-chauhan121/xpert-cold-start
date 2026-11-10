**Session 02 — Solution architecture design**

Prepared on 4 November 2026 for the XPERT Lab Cold Start Internship Challenge. This is an architecture proposal, not implementation code, a benchmark report, or a conversation transcript. The user authorized this document only. Session 01's technical report and transcript are to remain unchanged. No solution, checker, model request, or development-answer access is part of this phase.

**Recommendation and beginner's mental model.**

Build a staged, evidence-preserving Python pipeline. Use ordinary Python to organise data, enforce constraints, track state, schedule work, and write the final JSON. Use one configured multilingual LLM for interpreting ambiguous language and resolving difficult relationships between facts. Start with a compact model and a bounded number of selective review calls, rather than one call per message or an autonomous collection of agents.

Think of the system as a careful analyst with two notebooks. The first is a relationship directory: people, organisations, and chat ownership. The second is a task ledger: what was requested, who owes it, what changed, and which message proves the change. Every note points back to the original messages. The model proposes interpretations; Python checks references and applies consistent rules. A final exporter copies only permitted fields into the challenge output.

The first reading pass extracts reusable evidence for all categories together. Later decisions are separated by responsibility so that a correction to a relationship does not require reading every message again. Internal records can express uncertainty and multiple possibilities; the final schema cannot always do so. That mismatch must be handled explicitly rather than hidden.

**Verified requirements and limits of the evidence.**

The starter's actual `schema.json`, `check.py`, `README.md`, `llm.py`, `solution.py`, and `run.sh`, the data README, and the supplied challenge PDF were inspected. Source files and the schema were re-read for this phase. The development answer keys were not opened. Session 01 established the input statistics below using input files only.

| Verified requirement or observation | Consequence for the design |
|---|---|
| The output contains exactly `people`, `organisations`, `chats`, `goals`, and `open_loops`. | Internal debugging and confidence fields must be removed at export. |
| People have one allowed circle; `ME` is excluded from the people array. | Maintain one global classification per input person rather than different circles in different chats. |
| Every chat maps to exactly one person or organisation. | Final coverage and uniqueness checks are mandatory. A group is not automatically an organisation. |
| Organisation IDs are solution-defined and matched through attached chats and people. | Focus on correct grouping rather than reproducing development names. |
| Goals have evidence and at most ten entries. | Emit supported goals, not a quota of ten guesses. |
| Loops have source, owner, type, and final status; done/dropped work belongs in the output too. | Keep completed and cancelled tasks in the ledger rather than deleting them. |
| The brief asks for closure evidence and action-specific assistance details. | Enforce those semantics in addition to the schema's weaker optional-field rules. |
| The checker is hand-written and does not load the JSON Schema. | Passing the checker is not sufficient validation. |
| Dev has 4,502 messages, 138 chats, 286 other participants, ten seeded circles, two organisation names, and no seeded goals. | Read actual seed content; do not assume the quantities in illustrative descriptions. |
| Dev has no non-null quoted IDs and contains media placeholders. | Missing reply structure and attachment content are normal conditions, not fatal errors. |
| Hidden evaluation is approximately 15,000 messages over six later weeks, with names changed again. | Rules and prompts must generalise from evidence rather than memorised names or IDs. |
| Loop evaluation concerns the hidden set's last two weeks; earlier weeks provide context. | Process the whole supplied history. Do not read answer metadata or discard early evidence. |
| Goals and help decisions are unlabelled in dev; other labels are incomplete/imperfect according to the data README. | Report official and manually reviewed quality separately. |
| The run has a 30-minute limit in a clean Linux environment, with network access only to the model endpoint. | No runtime package downloads, web search, model downloads, or external retrieval services. |
| Model configuration is supplied through `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. | Do not hardcode a second endpoint or silently switch models. |
| Fine-tuned and self-hosted models are prohibited by the supplied PDF. | Choose a hosted compatible model; ordinary local processing remains available. |

The full point allocation is circles 12, organisations 8, chats 8, goals 8, loops found 14, loop status 14, help 10, cost 12, write-up 7, and one-command execution 7. The loop-related components total 38 points, relationships/organisations/chats total 28, and cost plus execution total 19. These are prioritisation inputs, not permission to omit required output fields.

All chunk sizes, budget allocations, retry limits, confidence rules, module names, and acceptance targets below are proposed engineering choices. None is an invented challenge requirement. No measured accuracy, cost, or runtime is claimed.

**Overall components and end-to-end data flow.**

1. Configuration and input gate: resolve the three allowed input filenames, runtime settings, and the configured endpoint. Record a fingerprint of the run inputs and configuration. Never recursively discover or load answer files.
2. Normalised input store: retain original records and construct indexes by message ID, chat ID, person ID, and timestamp. This is the immutable evidence store: derived decisions must not alter the source records.
3. Context planner: divide chat histories into bounded conversation windows, attach relevant seed facts, build reply/participant references, and record which messages each window covers.
4. Shared evidence extractor: use an LLM to identify relationship clues, organisation clues, goal candidates, new tasks, and task-update events within each window. Its output is intermediate structured JSON, not the final submission object.
5. Evidence validator and merger: check all cited IDs and spans, combine observations from overlapping windows, and retain ambiguous updates for later resolution.
6. Relationship resolver: combine evidence across chats to decide circles, organisation membership, staff care links, and chat assignments. Resolve organisations and people jointly in a bounded sequence rather than assuming either is already perfect.
7. Goal resolver: merge candidates, verify the user's intention and evidence, assign allowed categories/horizons, and rank no more than ten supported goals.
8. Task reconciler: link observations to existing tasks, track updates in chronological order, and use focused LLM review for ambiguous matching, completion, cancellation, or reopening.
9. Help policy: consider the final open tasks, ownership, sensitivity, and useful next action; choose assist, remind, or leave with the requested details.
10. Final validation and export: enforce the actual schema, identifier integrity, complete coverage, and semantic invariants; sort deterministically and write a single output file safely.
11. Independent evaluation: only after an approved inference run, compare its frozen output with references in a separate evaluation process. This stage is never imported by the inference pipeline.

The model gateway, request cache, usage ledger, and runtime scheduler support steps 4–9. They do not decide what constitutes a family relationship or task completion. The pipeline owns those responsibilities explicitly.

The main dependencies are: raw inputs → windows → evidence; evidence → relationship directory and task/goal candidates; relationship directory plus task events → reconciled tasks; reconciled tasks plus relationship directory → help; all resolved categories → validation → final JSON. Goals can be resolved alongside task reconciliation once relationship evidence is available. There is no need for a single global LLM call containing the entire history.

**Loading and preprocessing.**

Use UTF-8 and read JSONL one nonblank line at a time. A JSONL file contains an independent JSON record per line. Retain original text, IDs, sender identity, timestamp, kind, and quoted ID. Store original line position for reproducible ordering when timestamps tie. Reject duplicate conflicting IDs and missing essential fields with clear diagnostics rather than silently overwriting records.

Build a person registry from chat participants, excluding `ME`, and index senders as evidence about those IDs. Report a sender absent from all participant metadata instead of inventing a new identity mapping. Keep zero-message chats and silent participants: the final coverage rules still apply to them. Parse seed circles as authoritative supplied facts; seed organisation names are anchors, not fully specified organisation records. A seed goal still needs actual message evidence before it can satisfy the output goal schema.

Group messages by `chat_id`, then stable-sort by timestamp and original line position. Use the input's maximum valid timestamp as the global end-of-data time, called `as_of`. This gives reproducible final status and reminder planning. Do not use today's wall-clock date to interpret a historical conversation. Use a monotonic clock separately to enforce runtime budgets; that clock must not affect inferred due dates.

Preserve raw content and construct a separate normalised search representation. Unicode normalisation, case folding for matching, and whitespace handling can improve retrieval, but must not overwrite the original evidence. Do not indiscriminately strip emojis, punctuation, numbers, negation, or short replies: they can change meaning. Repeated identical text with different IDs remains distinct evidence. Forwarded advertisements can be marked as likely low relevance, but should not be silently dropped before any semantic reading.

Represent explicit dates and relative date phrases separately internally. Python can convert a resolved calendar expression into a date. An LLM is useful for ambiguity such as whether Hindi `kal` means yesterday or tomorrow in context. Do not mechanically resolve every relative expression using a keyword dictionary. When a due date cannot be justified, retain null rather than invent one.

The dataset's semantic timezone is not explicitly specified in the inspected materials. Proposed initial policy: a documented configurable Asia/Kolkata default, recognising explicit timezone statements when present. This is an assumption awaiting confirmation, not a rule of the challenge. Preserve UTC timestamps regardless of the local-time choice. Overdue tasks remain open unless there is closure evidence; a passed deadline is not proof of completion.

**Conversation windows and evidence preservation.**

Start with windows bounded by estimated tokens, not a fixed number of messages. A one-word reply and a lengthy document should not count as equal context cost. A tentative starting range is 3,000–6,000 input tokens per extraction window, leaving room for instructions, retrieved context, and output. Tune this using measured extraction density and latency. A model's advertised maximum context is a ceiling, not a recommended prompt size.

Prefer natural boundaries, such as a substantial time gap or topic shift, while retaining a small overlap of neighbouring turns. A tentative overlap is up to 10–15% of window tokens, adjusted when a question/reply pair would otherwise be split. Keep explicit quoted antecedents where present; if an antecedent lies outside the window, retrieve it by ID. Label overlap messages as context and primary messages as the window's extraction responsibility.

The window manifest tracks every input message's primary window and whether that window was processed successfully. Primary coverage is distinct from repeated context coverage. No keyword-only filter should decide that a message can never contain a goal or loop. Initially, every message is eligible for the shared extraction pass; later cost reductions require an audited estimate of missed items. Very long messages are divided into overlapping spans under the same original message ID, with offsets for traceability rather than a silently truncated body.

Each observation records source IDs, any short supporting span, its subject, and its proposed interpretation. Retain the source window and prompt version. Verify that IDs exist and that quoted spans correspond to those messages. A valid citation is necessary but not sufficient: later review must also check that the cited words support the claim. Never ask a model to manufacture message IDs from memory.

Windows may be extracted independently for parallelism. If an isolated update such as a short completion reply cannot be assigned locally, preserve it as an unresolved update event rather than dropping it or inventing an antecedent. The later task reconciler uses chronology, nearby messages, known participants, and a ledger of candidate tasks to resolve it. This avoids a long serial chain of LLM summaries while retaining cross-window continuity.

When replies are missing, adjacency and topic similarity are clues, not proof of a reply relation. Keep internal candidate links and their supporting evidence; never rewrite an absent `quoted_id` as an established fact. A message containing only a media placeholder supplies its existence, sender, kind, and time, not the attachment's contents. Nearby text may establish what it means. The system should not claim to have read a receipt, document, or photograph that is unavailable.

**Multilingual handling and bounded retrieval.**

Pass English, Hindi, Bengali, and Hinglish text in its original script to a model benchmarked on those languages. Avoid translating the whole dataset up front: translation adds cost and can change kinship terms, negation, tense, or politeness. For a genuinely ambiguous phrase, a selective model review may include an internal translation alongside the original; evidence always points to the original message. Language detection is a routing clue, not a reason to reject mixed-script messages. Do not infer a person's relationship from language, surname, or an honorific alone.

Keep compact per-chat and per-person evidence cards. A card is a short list of supported facts and unresolved alternatives with source IDs, not an unrestricted prose biography. Retrieve relevant original messages when deciding a conflict. Maintain three context layers: local conversation turns, compact relationship/task state, and targeted original evidence. Summaries must never become the sole proof of a final claim.

Start retrieval with IDs, participants, organisation aliases, time range, and character/token overlap. A character-based index can handle script and spelling variation without an additional embedding endpoint. Keyword matching is only for finding candidate evidence, not classifying semantics. Add embeddings later only if measured recall failures justify the dependency, model availability, cost, and allowed endpoint. An embeddings API cannot be assumed from Chat Completions compatibility or from a single configured chat model.

If a compact context packet exceeds its budget, partition the relevant candidates and evaluate all partitions as needed; do not silently evict old unresolved tasks. Completed tasks remain searchable for later revisions or reopening. Retrieval limits must be measured against missed links, especially for short replies. Evidence cards and indexes make memory manageable, but no finite prompt budget guarantees perfect recall.

**Internal data model and uncertainty.**

Use simple typed records and dictionaries initially; a graph database and vector service are unnecessary. A graph here simply means relationships between objects, represented by IDs and lists in ordinary Python.

| Internal record | Contents and responsibility |
|---|---|
| Input record | Original message/chat fields and immutable provenance. |
| Evidence observation | Subject, proposed fact, message IDs/spans, extraction window, alternatives, and support strength. |
| Person profile | Seed circle if supplied; candidate circles; organisation links; care links; contradictions; supporting IDs. |
| Organisation candidate | Name aliases, associated people/chats, type/side/role hypotheses, merge evidence. |
| Chat profile | Participants, purpose evidence, candidate person/organisation targets, final choice. |
| Goal candidate | Intention, area/type/horizon candidates, ownership by the user, evidence, deduplication group. |
| Task record | Stable internal ID, canonical source, additional supporting origins, owner, action/object, due-date evidence, event history, current status, closure evidence. |
| Task event | Creation, acceptance, update, completion, cancellation, or reopening interpretation, with timestamp and supporting IDs. |
| Decision record | Final interpretation, evidence, uncertainty reason, and whether a fallback was used. |
| Request/run record | Input/config/prompt fingerprints, tokens, elapsed time, errors, retries, model identity, coverage, and cache status. |

An LLM-generated confidence number is not a calibrated probability. Prefer interpretable support categories: explicit statement, repeated contextual support, weak indirect clue, or unresolved contradiction. If numeric thresholds are later used, assess them against human review or held-out labelled examples. Use uncertainty to allocate review calls, not to claim statistically justified certainty.

The final schema has no `unknown` circle or unknown chat target. For a poorly supported required decision, retrieve additional evidence and perform one focused review. Then select the best-supported allowed alternative using a stable tie policy, and record low support internally. If there is literally no useful evidence for a person's circle, a documented last-resort `friend` fallback may maintain coverage, but it is an unverified guess and must be counted separately. Do not represent it as inferred truth or let it generate further confident claims. This fallback is a known design weakness to evaluate, not a recommended default for ordinary cases.

For chats with weak evidence, prefer a supported existing target and a focused review; do not create a new organisation just to remove ambiguity. With no defensible mapping, record the degraded decision explicitly in diagnostics. The external schema forces a choice, so the system cannot honestly promise both perfect certainty and universal coverage. Optional unsupported links and goals can be omitted, while required-field decisions need the explicit uncertainty policy.

**Reasoning responsibilities by component.**

| Component | Deterministic Python responsibility | LLM responsibility |
|---|---|---|
| People/circles | Apply seed facts, collect evidence across chats, enforce one circle and valid IDs, preserve corrections. | Interpret roles, kinship, work relationships, and conflicting contextual clues. |
| Organisations | Maintain candidate memberships/aliases, stable IDs, merge bookkeeping, uniqueness. | Decide whether the user belongs to/runs an entity; infer type, side, role, and meaningful equivalence. |
| Chat assignment | Guarantee one target per chat, resolve target IDs, supply direct-chat candidates. | Interpret group purpose and ambiguous direct/group ownership. |
| Goals | Gather/deduplicate candidates, enforce ten-item limit and evidence requirements. | Distinguish user intentions from tasks, quotations, promotions, and other people's goals. |
| Loop detection | Ensure coverage, preserve origins, validate candidate records. | Recognise commitments, followups, deadlines, and pending questions in context. |
| Ownership | Resolve explicit speaker/participant IDs and enforce allowed references. | Resolve pronouns, addressees, delegation, and whether an action is actually owed. |
| Task reconciliation | Sort events, preserve histories, enforce valid transitions, exact-match strong references. | Decide whether two observations concern the same task and whether completion/cancellation is supported. |
| Help | Apply final-state and permission constraints; construct/validate times and required details. | Judge useful assistance, personal sensitivity, responsibility, and likely annoyance. |

**People, organisations, and chat assignment.**

People classification should use a profile assembled from all their chats, not just their display name. Explicit seed circles take precedence over model guesses. Keep contrasting evidence visible rather than letting a summary overwrite it. Do not invent a universal hierarchy such as family always overrides every other role: the output wants one circle, and the user's actual relationship should guide the decision. A later user correction should update the profile and invalidate dependent decisions without discarding unrelated evidence.

Organisation discovery begins with seed names and evidence that the user owns, runs, supports, resides in, or belongs to an entity. Use participants, aliases, activity, and chat purpose to propose merges. Shared participants alone are insufficient: the same person can participate in home, work, and social groups. Do not create client companies merely from mentions, and do not force every group into a new organisation. Empty organisation candidates should be reviewed for unsupported invention rather than retained only because a name was extracted.

Assign deterministic organisation IDs after merging, for example from a stable ordering of supported membership and canonical source IDs, with collision handling. Names remain presentation labels. Avoid model-generated random IDs or IDs derived solely from names, which change in the hidden set.

Resolve this interdependence in a bounded sequence: collect evidence → propose people/organisation candidates → perform initial grouping → assign chats/links → inspect contradictions once. This is preferable to unlimited iterative reconsideration. Shared evidence does not become independent proof merely because two model stages repeated it.

A normal direct chat has a natural person target, so use that as a strong structural default subject to contrary contextual evidence. For groups, ask whether the group's purpose belongs to the user organisation or to a particular person. A child's parent group can belong to the child. The target must be a real input person or a discovered organisation, not an invented persona. Staff `looks_after` and `supports` links need specific evidence; being in the same group does not establish care or employment.

**Goal extraction.**

Extract intentions expressed or adopted by the user, including a conversational reply confirming a goal. Separate a recurring habit, a measurable milestone, and a planned experience from the immediate steps supporting it. A plan to take a family trip may be a goal while booking accommodation is a loop; both can exist with distinct purposes and evidence. A forwarded advertisement or somebody else's ambition does not automatically become the user's goal.

Merge paraphrases about the same outcome, but do not merge distinct goals merely because they share an area. Select the allowed area/type/horizon from the actual schema. Horizon categories are coarse and the brief does not define exact boundary rules; document a consistent nearest-supported-category policy and flag inferred horizons internally rather than manufacturing dates. Rank supported candidates by evidence and importance, not by a desire to fill ten slots.

Cite the smallest useful set of actual supporting messages. Do not attach all messages to improve the chance of a scorer overlap. Evidence stuffing would conceal errors and destroy the meaning of evidence. If a seed goal lacks message evidence in this input, retain it as internal context instead of emitting an invalid evidence-free output goal.

**Task detection, ownership, and temporal state.**

First extract obligations and update events broadly enough to retain plausible work, then require evidence before promoting a candidate into the final ledger. Statements about completed past events, hypothetical plans, advertisements, rhetorical questions, and generic social questions need context before being treated as actionable loops. A candidate's source should be the message that actually raised the obligation or pending decision, not automatically the latest reminder.

Preserve all plausible source evidence internally but export one canonical origin. Choose it by the conversation semantics, never by consulting acceptable answer IDs. A single message can raise multiple tasks; deduplication must consider action/object, owner, and context, not just `source_msg`. Conversely, several messages can update one task. Do not generate a fresh loop for every followup mention.

Resolve ownership from the obligation: first-person promises normally refer to the speaker; requests require resolving the addressee; waiting-on-someone tasks belong to that person. A task's owner is not automatically its sender or `ME`. For unclear group requests, retain ambiguity until more context appears. Prefer precise actions over compound titles that mix different owners or completion criteria.

The allowed loop types overlap semantically. Proposed consistent policy: use the main unresolved issue to choose the type. A pending decision is a question; waiting for somebody else's deliverable is a followup; the user's explicit promise is a commitment; a date-driven requirement without a clearer promise/followup is a deadline. Due dates can accompany any type. This is a proposed annotation convention to test, not a new official precedence rule.

The task ledger is an event history, not just a final label. Python orders validated events and maintains state. Explicitly supported completion can move open → done; cancellation can move open → dropped. Acknowledgment or revised due date leaves the task open. Expiration alone never closes it. Later evidence may reopen work; after reopening, obsolete closure evidence must not remain as the current `closed_by`.

Completion must match the scope of the obligation. Payment initiated is not necessarily payment received if the obligation was receipt. A request to revise a delivered document can be a reopening or a new related task; resolve it from the wording rather than a fixed keyword. A cancellation phrase in a quoted or negated message is not automatically cancellation.

Use candidate matching in layers: explicit reply/reference and same task identifiers first; then owner, action/object, temporal continuity, and shared context; finally focused LLM adjudication for ambiguous pairs. Search across chats only when there are strong linking cues. Cross-chat completion is possible, so do not require `closed_by` to be in the source chat; require a supported link and sensible chronology instead.

Illustrative scenario, not development data: one person promises to send a draft, the recipient says okay, a later message says it was sent, and then the recipient requests a revision. The okay is acknowledgement. The sent message may complete the original send obligation. The revision request needs a separately reasoned update/new task decision. The system must keep those observations rather than compress them into an unsupported single done label.

**Assist, remind, and leave.**

Make this decision only after task status and ownership are resolved. Done/dropped loops receive no help object. For open loops, ask what useful next step exists, who can perform it, whether it would intrude, and whether external action would need permission.

Use `assist` when a specific private/reversible step can move the user's work forward, such as preparing a draft or comparing already available options. `needs_yes` refers to that proposed step itself, not every hypothetical later action. Preparing a draft can be false; sending it externally would require true. Do not promise unavailable browsing or tools as if they were executed. Output is a proposal only.

Use `remind` when the user must personally decide or act and a reminder has a justified time. Anchor timing to the end-of-data time and contextual due date. A proposed local business-hours policy can supply a reproducible time when the text does not specify one, but it must be documented as a policy, not an extracted fact. Do not set reminders in the past or invent a deadline merely to justify a reminder.

Use `leave` when the task is being handled by somebody else, is too personal, or intervention is likely to annoy rather than help. Ownership alone is not an absolute rule: the user may legitimately need help following up on another person's obligation. Conservatism should reflect the asymmetric penalty for unwanted intervention, not a blanket leave-for-everything shortcut. Internally record the evidence and reason for the action choice; export only the allowed fields.
