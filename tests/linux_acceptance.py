"""Explicit, no-spend Section 9a acceptance; Linux CPython 3.9.25 only.

Run: python3.9 -B -S tests/linux_acceptance.py --report PATH
Uses only owned synthetic inputs, loopback HTTP and test-only launcher copies.
No production files are edited. Missing prerequisites are BLOCKED, never PASS.
"""
import argparse
import hashlib
import http.server
import json
import multiprocessing
import os
from pathlib import Path
import platform
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import llm
import solution

CASES = ("hang", "slow", "stall", "retry", "crash", "invalid", "ignore_term",
         "launcher_hang", "launcher_success", "interrupted_write")
TOLERANCE = 2.0


def network_guard(event, args):
    if event == "socket.connect" and args[1][0] != "127.0.0.1":
        raise RuntimeError("Acceptance permits loopback only")
    if event == "socket.getaddrinfo" and args[0] != "127.0.0.1":
        raise RuntimeError("Acceptance forbids external DNS")


sys.addaudithook(network_guard)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mark(folder, label, **extra):
    row = dict(event=label, at=time.monotonic(), pid=os.getpid(), pgid=os.getpgrp(), **extra)
    (Path(folder) / (label + ".json")).write_text(json.dumps(row), encoding="utf-8")


def worker(buffer, endpoint, body, key, deadline, max_bytes):
    case, folder = json.loads(body)
    mark(folder, "worker_started")
    if case == "crash":
        os._exit(7)
    if case == "invalid":
        buffer[:8] = struct.pack("!Q", 2)
        buffer[8:10] = b"xx"
        return
    if case == "ignore_term":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        mark(folder, "term_ignored")
    time.sleep(60)


class SlowHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(200)
        self.send_header("Content-Length", "100000")
        self.end_headers()
        try:
            for index in range(50):
                self.wfile.write(b"x")
                self.wfile.flush()
                self.server.progress.append(time.monotonic())
                time.sleep(60 if self.path == "/stall" else 0.15)
        except (OSError, ValueError):
            pass


class Events(list):
    def append(self, event):
        event = dict(event)
        if event["event"] == "start":
            event["pgid"] = os.getpgid(event["pid"])
        super().append(event)


def fixture(folder):
    for name in ("chats.jsonl", "messages.jsonl"):
        (folder / name).write_text("", encoding="utf-8")
    (folder / "seed.json").write_text("{}", encoding="utf-8")
    (folder / "output.json").write_bytes(b"existing-output-must-survive\n")


def inner_case(case, folder):
    output = folder / "output.json"
    old = digest(output)
    started = time.monotonic()
    events, dispatches, sleeps, progress = Events(), [], [], []
    summary, error = {}, None
    server = None
    deadline = llm.Deadline(network=6, exit_target=10, overall=20)
    transport = llm.ProcessTransport(worker=worker, grace=0.2)
    transport.events = events
    if case in ("slow", "stall"):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
        server.daemon_threads = True
        server.progress = progress
        threading.Thread(target=server.serve_forever, daemon=True).start()
        transport.worker = llm._http_worker

    def assembly(data, **kwargs):
        nonlocal error
        try:
            if case == "retry":
                def reject(*args):
                    dispatches.append(time.monotonic())
                    return 429, {"Retry-After": "7"}, b""
                client = llm.Client(transport=reject, deadline=deadline,
                                    budget=llm.Budget(planned_base_calls=10), sleep=sleeps.append)
                with patch.dict(os.environ, {"LLM_BASE_URL": "http://127.0.0.1",
                                             "LLM_MODEL": "synthetic", "LLM_API_KEY": "synthetic"}):
                    client.chat([{"role": "user", "content": "synthetic"}])
            else:
                dispatches.append(time.monotonic())
                endpoint = ("http://127.0.0.1:%d/%s" % (server.server_port, case)
                            if server else "unused")
                transport(endpoint, json.dumps([case, str(folder)]).encode(), "synthetic", 3)
        except llm.LLMError as exc:
            error = exc.detail["code"]
            raise
        raise AssertionError("Failure scenario unexpectedly succeeded")

    try:
        with patch.object(solution, "assemble_output", assembly):
            status = solution.main(folder, output, deadline=deadline, summary=summary)
    finally:
        if server:
            server.shutdown()
            server.server_close()
    elapsed = time.monotonic() - started
    assert status == 1 and summary["state"] == "incomplete"
    assert digest(output) == old
    assert elapsed <= (3.5 if case != "retry" else 1) + TOLERANCE
    assert all(at < deadline.started + deadline.network for at in dispatches)
    if case == "retry":
        assert len(dispatches) == 1 and not sleeps and error == "deadline"
    else:
        assert events[-1]["event"] == "reaped"
        assert events[0]["pgid"] == os.getpgrp()
        pid = events[0]["pid"]
        assert not Path("/proc/%d" % pid).exists(), "Worker remains alive or zombie"
        assert not multiprocessing.active_children()
        reaped = events[-1]
        if case in ("hang", "ignore_term"):
            assert error == "timeout"
            terminate = next(e for e in events if e["event"] == "terminate")
            assert reaped["at"] - terminate["at"] <= 2 * transport.grace + TOLERANCE
        if case == "ignore_term":
            assert (folder / "term_ignored.json").exists()
            assert any(e["event"] == "kill" for e in events)
            assert reaped["exitcode"] == -signal.SIGKILL
        if case == "crash":
            assert error == "worker_failure" and reaped["exitcode"] == 7
        if case == "invalid":
            assert error == "worker_failure" and reaped["exitcode"] == 0
        if case in ("slow", "stall"):
            assert progress and error in ("timeout", "network")
            assert len(progress) >= (2 if case == "slow" else 1)
    return dict(case=case, status="PASS", elapsed=elapsed, application_exit=status,
                stage=summary["state"], error=error, events=events, dispatches=dispatches,
                cutoff=deadline.started + deadline.network, response_progress=progress,
                before_sha256=old, after_sha256=digest(output), pgid=os.getpgrp())


def launcher_inner(case, folder):
    folder = Path(folder)
    mark(folder, "main_started")
    if case == "launcher_hang":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        subprocess.Popen([sys.executable, "-B", "-S", __file__, "--orphan", str(folder)])
        time.sleep(60)
    elif case == "interrupted_write":
        def partial_dump(value, stream, **kwargs):
            stream.write('{"incomplete":')
            stream.flush()
            mark(folder, "partial_written")
            time.sleep(60)
        with patch.object(solution.json, "dump", partial_dump):
            raise SystemExit(solution.main(folder, folder / "output.json"))


def group_members(pgid):
    found = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            fields = (path / "stat").read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) == pgid:
                found.append(dict(pid=int(path.name), state=fields[0], pgid=pgid))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return found


def run_case(case, folder):
    fixture(folder)
    old = digest(folder / "output.json")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("LLM_", "PYTHON"))}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    launcher = case.startswith("launcher_") or case == "interrupted_write"
    if launcher:
        # Pin the launcher's python3 to the already running 3.9.25, offline.
        bindir = folder / "bin"
        bindir.mkdir()
        (bindir / "python3").write_text('#!/bin/sh\nexec "%s" -B -S "$@"\n' % sys.executable)
        (bindir / "python3").chmod(0o700)
        env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
        script = PROJECT / "run.sh"
        if case != "launcher_success":
            text = script.read_text(encoding="utf-8")
            assert text.count("--kill-after=2s 1770s") == 1
            script = folder / "run.sh"
            script.write_text(text.replace("--kill-after=2s 1770s", "--kill-after=1s 12s"))
            (folder / "solution.py").write_text(
                "import sys\nsys.path.insert(0, %r)\nfrom linux_acceptance import launcher_inner\n"
                "launcher_inner(%r, %r)\n" % (str(PROJECT / "tests"), case, str(folder)))
        command = ["bash", str(script), str(folder), str(folder / "output.json")]
    else:
        command = [sys.executable, "-B", "-S", __file__, "--inner", case, str(folder)]
    started = time.monotonic()
    process = subprocess.Popen(command, env=env, cwd=PROJECT, start_new_session=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    observed = []
    try:
        stdout, stderr = process.communicate(timeout=20)
        elapsed = time.monotonic() - started
        # GNU timeout creates its own group: record that group from inner markers.
        markers = [json.loads(p.read_text()) for p in folder.glob("*.json")
                   if p.name in ("main_started.json", "orphan_started.json", "partial_written.json")]
        groups = {process.pid} | {row["pgid"] for row in markers}
        limit = time.monotonic() + TOLERANCE
        while True:
            observed = [row for group in groups for row in group_members(group)]
            if not observed or time.monotonic() >= limit:
                break
            time.sleep(0.05)
        assert not observed, "Run-owned processes remain: %r" % observed
        total = time.monotonic() - started
        bound = 20 if case == "launcher_success" else 15
        assert total < bound, (total, bound)
        if not launcher:
            assert process.returncode == 0, stderr[-2000:]
            row = json.loads(stdout)
        else:
            expected = 0 if case == "launcher_success" else (137 if case == "launcher_hang" else 124)
            assert process.returncode == expected, (process.returncode, stderr[-1000:])
            if case == "launcher_success":
                assert json.loads((folder / "output.json").read_text()) == {
                    key: [] for key in ("people", "organisations", "chats", "goals", "open_loops")}
            else:
                assert digest(folder / "output.json") == old
                marker = "orphan_started.json" if case == "launcher_hang" else "partial_written.json"
                assert (folder / marker).exists(), "Failure injection did not run"
            row = dict(case=case, status="PASS", markers=markers,
                       stage="succeeded_empty" if expected == 0 else "interrupted",
                       before_sha256=old, after_sha256=digest(folder / "output.json"))
        row.update(command=command, launcher_exit=process.returncode,
                   harness_elapsed=time.monotonic() - started, remaining_processes=observed)
        return row
    finally:
        # Emergency cleanup cannot turn a failed test into a pass.
        groups = {process.pid}
        for name in ("main_started.json", "orphan_started.json"):
            if (folder / name).exists():
                groups.add(json.loads((folder / name).read_text())["pgid"])
        for group in groups:
            try:
                os.killpg(group, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.communicate(timeout=2)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = dict(platform=platform.platform(), python=sys.version, executable=sys.executable,
                  start_method="spawn", cases=[], scheduling_tolerance=TOLERANCE,
                  network="loopback only; external connect and DNS audit-denied")
    if sys.platform != "linux" or sys.version_info[:3] != (3, 9, 25):
        report.update(status="BLOCKED", reason="Requires Linux CPython 3.9.25")
    elif not shutil.which("timeout") or not shutil.which("bash"):
        report.update(status="BLOCKED", reason="Missing existing timeout or bash")
    else:
        report["os_release"] = Path("/etc/os-release").read_text()
        report["timeout_version"] = subprocess.check_output(["timeout", "--version"], text=True).splitlines()[0]
        for name in ("data", "llm", "reasoning", "tasks", "validation", "solution"):
            __import__(name)
        assert sys.flags.no_site, "Run with -S to verify offline packaging"
        solution.SchemaValidator()
        deadline = llm.Deadline()
        assert (deadline.network, deadline.exit_target, deadline.overall) == (1620, 1770, 1800)
        assert "--kill-after=2s 1770s" in (PROJECT / "run.sh").read_text()
        report["packaging"] = "Six modules imported with -S; selected SchemaValidator constructed"
        report["production_constants"] = dict(network=1620, exit=1770, kill_grace=2, overall=1800,
                                               residual_margin=28)
        with tempfile.TemporaryDirectory(prefix="h1-linux-", dir=PROJECT / "tests") as temp:
            for case in CASES:
                folder = Path(temp) / case
                folder.mkdir()
                try:
                    row = run_case(case, folder)
                except Exception as exc:
                    row = dict(case=case, status="FAIL", error=str(exc))
                report["cases"].append(row)
                print(case + ": " + row["status"], flush=True)
        report["status"] = "PASS" if all(r["status"] == "PASS" for r in report["cases"]) else "FAIL"
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["status"], flush=True)
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--inner":
        print(json.dumps(inner_case(sys.argv[2], Path(sys.argv[3]))))
    elif len(sys.argv) > 1 and sys.argv[1] == "--orphan":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        mark(sys.argv[2], "orphan_started")
        time.sleep(60)
    else:
        raise SystemExit(main())
