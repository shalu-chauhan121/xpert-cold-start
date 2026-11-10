# Write-up

## What I focused on, and why

I focused on building a reliable cold-start pipeline that converts raw chat exports (people, chats, messages and signup seed information) into five structured output categories: people, organisations, chats, goals and open loops.

The central design priority was reliability rather than silently maximising output. The pipeline uses evidence-backed observations, strict validation, deterministic resolution and explicit incomplete or pending states. Unsupported or ambiguous results should fail closed instead of being presented as successful predictions. I also built a bounded live-pilot workflow to test model behaviour on synthetic multilingual fixtures without automatically authorising a full run.

## My approach

The implementation uses Python 3.9+ and standard-library modules organised around six responsibilities:

- **`data`** — loads and indexes chat data and creates exactly-once 4,000-character processing windows with up to two context spans.
- **`validation`** — enforces the output schema and rejects unsupported or malformed records.
- **`llm`** — handles OpenAI-compatible model requests, structured failures, shared usage reservations, caching, worker transport and deadlines.
- **`reasoning`** — extracts evidence-backed observations and resolves people, organisations, entities and goals.
- **`tasks`** — interprets task-related messages and matches open-loop events within and across chats.
- **`solution`** — coordinates the pipeline and writes the five output arrays through deadline-gated, atomic output handling.

Model responses are parsed and validated against the original message bodies. Evidence references are checked rather than trusted, and merges are deterministic. Conflicts and incomplete results remain explicit. The implementation uses an OpenAI-compatible API interface with structured JSON output.

### Model and bounded pilot

The selected model is `gemini-3.5-flash-lite`. The pilot was designed around 25 planned base dispatches across four synthetic multilingual fixture packs. Its configured safety envelope includes:

- Maximum 30 transmissions and 5 recoveries.
- A 250,000-token reservation.
- A 600-second network deadline.
- A USD 2.00 internal paid-equivalent safeguard.
- Fail-closed checks for real-mode execution.

The live pilot used synthetic fixtures only. It did not use hidden evaluation data. The configured Free tier was used, with no paid fallback or billing-enabled execution.

## What it costs

The implementation is designed to keep model usage as the primary variable cost. There are no additional paid infrastructure dependencies in the pipeline.

Based on the pricing figures recorded during the project's research, the Standard paid rates used for estimation were approximately **$0.30 per million input tokens and $2.50 per million output tokens**. The Free tier used for the bounded pilot was free of charge.

The configured pilot envelope was estimated at approximately **$0.16 maximum paid-equivalent cost**, below the internal USD 2.00 safeguard. This is a planning estimate, not a claim that a paid run was performed.

For the development dataset measured earlier (4,502 messages, 138 chats and 280 processing windows), the extraction estimate was approximately 1.43 million input tokens plus reserved completion capacity, giving an estimated extraction cost of approximately **$1.86 at the recorded Standard rates**. Additional downstream model calls depend on actual outputs and are not included in that extraction-only estimate.

Actual cost depends on provider tokenisation, response lengths, retries and model availability. Usage reservations and limits are intended to stop execution rather than silently exceed the configured budget.

## Where it's wrong

The system has important limitations:

- **Token estimation:** The estimator uses wire size rather than the provider's exact tokenisation. It can overestimate Latin text and underestimate mixed-script content. A reservation or budget overrun should stop execution.
- **Semantic accuracy:** Passing schema and provenance checks does not prove that an extracted person, organisation, goal or open loop is semantically correct. Recall and precision have not been established through a complete independent evaluation.
- **Evidence strictness:** A transcription mismatch or incorrect evidence span can cause an otherwise plausible observation to be rejected. This is intentional fail-closed behaviour, but it can reduce extraction coverage.
- **Scaling:** Packet and context limits have been tested on synthetic workloads. Unusual real-world conversations may exceed those limits and produce incomplete results.
- **Live execution:** Free-tier rate limits, transient provider errors, latency and retry limits can prevent a complete run. The pipeline may stop early rather than claim success.

### Latest validation — 10 November 2026

The latest bounded live validation (Session 12) used `gemini-3.5-flash-lite` on four synthetic multilingual fixture packs. It completed within the configured envelope, using **15 transmissions and 3 recoveries**, with a runtime of approximately **80.4 seconds**.

The run attempted 11 of the 25 planned jobs. Extraction succeeded in 4 of 7 attempted windows. Downstream stages were consequently gated where prerequisite extraction was incomplete.

The run identified the following issues:

1. An English organisation observation cited an incorrect evidence span and was rejected by provenance validation.
2. A Hindi voice-transcription mismatch caused strict evidence-text validation to fail.
3. A Bengali capture exceeded the configured capture-size limit, making that case inconclusive.
4. A task-matching response returned a `none` decision without evidence, while the current validator requires evidence for that response.
5. The help stage returned an epoch-style timestamp instead of the requested ISO timestamp.

These findings show that the pipeline detects and rejects several unsupported outputs, but also that prompt compliance and end-to-end coverage remain incomplete.

The offline regression suite and earlier Linux/Python compatibility checks provide additional evidence for implementation readiness. However, offline tests and synthetic pilots cannot establish performance on the hidden evaluation set.

**Gate 6: NOT PASSED.** The latest run demonstrated bounded execution and identified concrete failure cases, but did not complete the required end-to-end validation. Semantic accuracy on the hidden dataset remains unverified. A full run should only be undertaken after the outstanding contract and evidence issues are addressed and the required approval gates are satisfied.