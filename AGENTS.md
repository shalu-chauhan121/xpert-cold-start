# XPERT project instructions

1. Follow the approved architecture and implementation plan in `ai-logs/codex/session-02-revised-implementation-plan.md`. Consult `ai-logs/codex/progress-checkpoint.md` for current status. Identify a concrete issue before proposing a redesign of approved decisions.
2. Implement only one explicitly approved stage at a time. Never proceed to the next stage without the user's approval.
3. Read only files relevant to the current task. Avoid unnecessary repository-wide inspection and repeated explanations.
4. Preserve completed implementations. Modify completed stages only when necessary, and explain the reason before making changes.
5. Add focused tests for code changes. Run relevant tests and report exact commands, results, and failures. Documentation-only changes require content and location checks, not code tests.
6. Never access `data/dev/answers/` during solution development or inference. Never use answer data to influence predictions.
7. Never expose, log, commit, or hardcode API keys, credentials, or secrets.
8. Preserve existing AI transcripts and reports. Append genuine work only; never fabricate conversation, logs, or results. Disclose inaccessible history.
9. Keep reports and Codex responses concise. Report changed files, implementation summary, test results, limitations, and the next stage's approval status.
10. Do not make unapproved API calls, install unnecessary dependencies, or expand the task scope.
