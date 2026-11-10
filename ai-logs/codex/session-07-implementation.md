# Session 07 - Stage E partial implementation

Stage D was approved by the user. Stage E is NOT complete. This is a saved
extraction milestone; context resolution must still be implemented before review
as a completed stage. No Stage F/G work occurred.

Created reasoning.py and tests/test_reasoning.py. Existing runtime files and
existing tests are unchanged. Extraction uses one versioned prompt and an injected
run-owned client. It checks exact primary coverage, known subject/evidence IDs,
supplied-slice boundaries and exact supporting text. Deterministic observation
IDs and exact deduplication preserve every contributing window. Failed windows
retain explicit incomplete state and valid partial results. Task observations
remain proposals without matching or replay. Semantic support is not proven by
substring validation or by fake model responses.

Verification on Windows/Python 3.12.9:
- python -B -m unittest discover -s tests -p test_reasoning.py -v
  8 tests in 0.006s, OK, no failures/errors, exit successful.
- python -B -m unittest discover -s tests -v
  175 tests in 12.176s, OK, 0 failures/errors, process exit 0.
Both commands ran sequentially in one PowerShell invocation. Output excerpts
were truncated by the tool, but the actual unittest summaries were retained.

Remaining mandatory work: bounded context-resolution requests, canonical
organisations and supported aliases; globally consistent people/circles/links
and chat targets preserving seeds; complete entity-batch accounting; semantic
goal dispositions, merging and the exact section 4a tier/ranking rules including
timezone date boundaries and maximum ten; focused acceptance tests for these.
Review extraction failure diagnostics and long-span/empty-input edge cases.
No model accuracy, Linux execution, Python 3.9 runtime or production readiness
claim. Python 3.9 grammar passed for reasoning.py. No real API calls, payments,
answer access, evaluator imports, installs or full-dataset execution occurred.

Next resume step: read plan section 4a in full, then implement organisation
resolution in reasoning.py using existing extracted observations and original
cited evidence; add synthetic canonical-alias and shared-participant tests.
Continue the already authorized Stage E; do not restart extraction or start F.

## Continuation - Context resolution implemented

This append supersedes the earlier extraction-only status without removing it.
Read AGENTS.md, Session 07 report, existing extraction code, and revised-plan
sections 4, 4a, 4b and 11, including the full six-part ranking rule.

Changed reasoning.py; added tests/test_reasoning_resolution.py. Preserved the
original eight extraction tests and every Stage A-D runtime/test file. Updated
only Session 07 documentation and appended checkpoint. No Stage F/G integration.

Added resolve_organisations, resolve_entities, rank_goals and resolve_goals.
One versioned context prompt complements the existing extraction prompt. Caller
supplies its run-owned client; no new client/network boundary exists. Responses
are validated both through the client's callback and before local acceptance.
The actual schema validates output records without changing validation.py.

Organisation groups explicitly partition candidate IDs into canonical groups,
reasoned rejections or pending decisions. IDs derive from sorted members;
aliases require quoted supporting text. Shared participants alone do not merge
entities. Entity batches cover requested IDs exactly once, preserve seed circles,
validate organisation/care/chat references and retain provenance. Missing/null or
failed decisions stay pending/incomplete. A person receives one global record;
group chats may target people. No blanket fallback is introduced.

Goal groups represent model-reviewed semantic equivalence, not lexical/area
merging. Rejected promotions/tasks/other-person intentions have reason codes;
failed review remains pending. Python checks original ME support, adoption
antecedents, independent text/episodes, explicit/pursuit/corroborated tiers and
ranks by tier, capped distinct local dates, latest positive ME time, earliest
support time, sorted IDs and stable span/category/normalised-title key. Ranking
keeps at most ten with no padding or area quota. Internal ranks/rejections are
separate from output fields. UTC is the explicit API default; callers can supply
another tzinfo and policy label, included in request context. This is a configurable
engineering policy, not an inferred dataset timezone.

Extraction retains its original interfaces and eight tests. Diagnostics now
separate invalid responses from request failures without logging private text.
Additional tests cover empty input and long-message span acknowledgements.

Executed on Windows/Python 3.12.9, project cold-start working directory:
- python -B -m unittest discover -s tests -p 'test_reasoning*.py' -v
  Initial continuation: 19 tests, 0.040s, OK, exit 0.
- python -B -m unittest discover -s tests -p 'test_reasoning*.py' -v
  Final focused: 23 tests, 0.051s, OK, 0 failures/errors.
- python -B -m unittest discover -s tests -v
  Final full suite: 190 tests, 12.476s, OK, 0 failures/errors, exit 0.
Final focused/full commands ran sequentially in one PowerShell invocation.

Limitations: semantic support, same-entity judgements, independent episodes and
forwarded-content labels remain model proposals, not proven by citation checks.
The tests do not establish real inference accuracy. Resolution packets are
bounded at a configurable 100000 UTF-8 bytes; oversized global organisation/goal
packets or entity context fail incomplete rather than silently omit candidates.
No scalable partition/merge recovery is implemented. Entity batching defaults to
32; context is repeated, so live token/latency feasibility needs later approval
and measurement. No live API, answer access, evaluator execution, installation,
download or full-dataset run occurred. Linux and actual Python 3.9 runtime remain
unverified; grammar check passes. No production-readiness claim.

Stage E resolver paths and synthetic module verification are implemented. Stop
for user review. Stage F remains unstarted and requires explicit approval.
