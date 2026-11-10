# OpenCode Session 01 — `launcher_hang` Linux acceptance fix

- **Date:** 2026-11-06
- **Agent:** OpenCode (GLM-5.3-Flash Free)
- **Environment:** Windows 11 host (PowerShell tool shell) driving WSL2 Ubuntu 26.04.1, uutils coreutils 0.8.0, uv CPython 3.9.25 (from the session-13 acceptance record).
- **Scope:** Section 9a / H1 gate 4 remediation only. No production Python files, acceptance harness, or tests were modified; no challenge data, answer/checker files, API calls, spending, or installations.

## Problem

`ai-logs/codex/session-13-linux-acceptance-ubuntu.json` recorded nine of ten Section 9a scenarios passing; `launcher_hang` failed with `Command ... timed out after 20 seconds`.

Root cause (diagnosed from `tests/linux_acceptance.py`, `run.sh`, the session-13 report, and the upstream sources of GNU coreutils `timeout` and uutils coreutils 0.8.0):

- GNU `timeout` delivers the `--kill-after` SIGKILL escalation to the **entire process group, including itself** (`src/timeout.c` `cleanup()`: direct `send_sig(monitored_pid, sig)` plus group-wide `send_sig(0, sig)`; its usage text documents "137 if COMMAND (or timeout itself) is sent the KILL signal"). The test's expected exit code 137 encodes this.
- Installed uutils `timeout` 0.8.0 (`ChildExt::send_signal_group` in `src/uucore/src/lib/features/process.rs`) attempts `signal(SIGKILL, SigHandler::SigIgn)` before its `kill(0, SIGKILL)`; POSIX rejects changing the SIGKILL disposition (EINVAL), the `?` aborts the helper, and the group-wide KILL is **never sent**. Only the direct KILL to the monitored pid lands.
- Consequently the TERM-ignoring orphan spawned by `launcher_inner` (`tests/linux_acceptance.py:189`, no stdio redirection) survives at ~13 s while holding the harness's stdout/stderr pipe write ends, `communicate(timeout=20)` at line 246 never sees EOF, and the 20 s harness cap converts the case into a `TimeoutExpired` FAIL whose emergency-cleanup `finally` masks the real launcher result.

## Change (the only file modified: `run.sh`)

Before (line 15):

```bash
exec timeout --signal=TERM --kill-after=2s 1770s python3 "$(dirname "$0")/solution.py" "$1" "$2"
```

After (lines 15–28):

```bash
# Some timeout implementations deliver the --kill-after KILL only to the
# monitored process (uutils coreutils <= 0.8.0 regressed the group-wide
# escalation in send_signal_group for SIGKILL), so TERM-ignoring group
# members could outlive the deadline. GNU timeout already signals the whole
# group and dies with it, which makes the killpg below a harmless no-op there.
# Deadline, kill grace and exit codes are unchanged: wait preserves timeout's
# status (0/1/124/137) exactly as the exec did.
set +e
timeout --signal=TERM --kill-after=2s 1770s python3 "$(dirname "$0")/solution.py" "$1" "$2" &
leader=$!
wait "$leader"
status=$?
kill -KILL -- "-$leader" 2>/dev/null
exit "$status"
```

Property mapping: deadline (`1770s`), kill grace (`2s`), exit-code passthrough (0/1/124/137), single supervised process group ($! is the group id because `timeout` `setpgid(0,0)`s), and the "one command" contract are all preserved. The killpg backstop is a no-op on GNU (group already empty) and flushes TERM-ignoring group leftovers only where a timeout implementation fails to escalate.

## Focused verification (exact commands and results)

The verifier imports the **unmodified** `tests/linux_acceptance.py` at its real path and calls `run_case(case, ...)` directly, so every case assertion (exit code, elapsed bound, marker files, output digest, leftover-process scan before `finally` cleanup) applies unchanged. Temporary directories are created under `tests/` with the same `h1-` prefix convention as the full suite; the verifier scripts themselves live in `C:\Users\Shalu Chauhan\AppData\Local\Temp\opencode\`, outside the repository.

Command 1 — `launcher_hang` only (fix applied):

```
wsl.exe -e /home/shalu_chauhan/.local/share/uv/python/cpython-3.9-linux-x86_64-gnu/bin/python3.9 -B -S '/mnt/c/Users/Shalu Chauhan/AppData/Local/Temp/opencode/verify_launcher_hang.py'
```

Result:

```
launcher_hang: PASS
launcher_exit = 137
harness_elapsed = 13.148461615999622
remaining_processes = []
markers = ['main_started', 'orphan_started']
```

Command 2 — `launcher_success` + `interrupted_write` only (regression check against the modified `run.sh`):

```
wsl.exe -e /home/shalu_chauhan/.local/share/uv/python/cpython-3.9-linux-x86_64-gnu/bin/python3.9 -B -S '/mnt/c/Users/Shalu Chauhan/AppData/Local/Temp/opencode/verify_launcher_cases.py'
```

Result:

```
launcher_success: PASS
  launcher_exit = 0
  harness_elapsed = 0.7052804140002991
  remaining_processes = []
  markers = []

interrupted_write: PASS
  launcher_exit = 124
  harness_elapsed = 12.265189685000223
  remaining_processes = []
  markers = ['main_started', 'partial_written']
```

All three results satisfy the harness assertions: exit codes 137/0/124 exactly as the original suite expects, elapsed under the 15 s (hang) / 20 s (success) bounds, no run-owned processes without emergency cleanup, both failure-injection markers present, and unchanged output digests.

One earlier shell attempt failed in PowerShell argument mangling (quoted heredoc content reaching bash with quotes stripped); it was replaced by the unwrap-free temporary-verifier invocation above. No test failure was involved.

## Limitations

- Only three of the ten scenarios (`launcher_hang`, `launcher_success`, `interrupted_write`) were executed on the modified `run.sh`, per instruction not to rerun the other seven or the full suite. Their previous PASS results are historical.
- Verification ran on the WSL2 Ubuntu 26.04.1 / uutils 0.8.0 image from session 13. Behavior under GNU `timeout` is reasoned from source (backstop proven no-op) but was not executed on a GNU host.
- `launcher_success`/`interrupted_write` outcomes are consistent with the change (identical timeout invocation path); they verify no regression in the covered scenarios, not platform-wide equivalence.
- The uutils group-escalation defect is an external-platform bug; this change defensively closes the survivable window rather than fixing the binary. A future uutils upgrade makes the backstop permanently idle.
- Python-side unit suites were not rerun; `run.sh` is not exercised by them.

Session transcript: the running OpenCode service (2.2.5, `http://127.0.0.1:28894`) exported the **actual, complete session** `ses_e52dfae70ffe2kTxngyH7TDTD0` ("launcher_hang acceptance root cause") via

```
opencode api get /api/experimental/session/ses_e52dfae70ffe2kTxngyH7TDTD0/export
```

(raw HTTP payload, byte-unmodified, captured with `cmd /c` binary redirection) into `ai-logs/opencode/session-01-transcript.json`: 609,456 bytes of `{"info", "messages"}` with 44 messages — 3 user prompts (including the original Plan-mode diagnosis request), 36 assistant messages, 44 tool parts with their inputs/outputs/completed/error states, 1 agent-switch record, and 2 synthetic messages. The raw API value is stored as-is; no records were added, removed, or fabricated. The export does **not** include any assistant response written after the export call (it was captured while this documentation task was still executing), and the earlier Plan-mode diagnosis session (`ses_e52e01d67ffeu9Cb3sEyBWIRiP`) is a separate OpenCode session whose raw export (351,440 bytes) was saved to the temp directory outside the repository. Existing Codex transcripts were not touched.
