"""Stage B: synthetic boundary probes; no real dataset or model service.

The solution has no model orchestration yet. Exercise its real validation/export
with a test-only output producer, separately from a Stage A -> HTTP client probe. The latter
compares nonempty wire payloads and fixed replies, not future extraction logic.
Each probe runs in a fresh interpreter so audit hooks cannot leak into Stage A.
"""

import argparse
import builtins
import dataclasses
import encodings.utf_8_sig  # Preload the loader's codec before guarding data reads.
import glob
import importlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import types
import typing
import unittest
import urllib.request
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
# Preload only the client's standard-library dependencies before the data guard.
# Its fresh module body is still executed under the guard below.
sys.path.insert(0, str(PROJECT))
import llm

INPUTS = ("chats.jsonl", "messages.jsonl", "seed.json")
DECOY = "SYNTHETIC_DECOY_MUST_NOT_REACH_INFERENCE"
FIXED_REPLY = {"observation": "synthetic fixed reply", "source_ids": ["M1"]}


def _probe(folder, attack=""):
    """Child process: guard runtime initialization and all subsequent work."""
    folder = Path(folder).resolve()
    # Read precisely named Python source before the data-read guard, without
    # executing it. Stdlib dependencies above are likewise preloaded. Fresh
    # module bodies below execute under the guard, including their imports.
    sources = {}
    for name in ("data", "llm", "validation", "solution"):
        source = (PROJECT / (name + ".py")).read_text(encoding="utf-8")
        if attack == "import_init" and name == "solution":
            source += "\nimport check\n"
        sources[name] = compile(source, str(PROJECT / (name + ".py")), "exec")

    def key(path):
        # No resolve/stat here: auditing an attempted open must not touch it.
        return os.path.normcase(os.path.abspath(os.fsdecode(path)))

    allowed_reads = {key(folder / name) for name in INPUTS}
    allowed_reads.add(key(PROJECT / "schema.json"))
    output = folder / "output.json"
    usage = folder / "usage.jsonl"
    allowed_writes = {key(output)}
    temporary_paths = set()
    report = {"reads": [], "writes": [], "imports": [], "violations": [],
              "requests": [], "ok": False}
    active = True
    phase = "initialization"

    def deny(operation):
        report["violations"].append(operation)
        raise AssertionError("Forbidden boundary operation: " + operation)

    def audit(event, args):
        if not active:
            return
        if event == "open":
            path, mode, flags = args
            if not isinstance(path, (str, bytes, os.PathLike)):
                deny("open:file-descriptor")
            target = key(path)
            # O_ACCMODE is not exported on Windows; these access bits are.
            access = flags & (os.O_WRONLY | os.O_RDWR)
            writing = access != os.O_RDONLY or flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            is_temp = (Path(target).parent == Path(key(folder)) and
                       re.fullmatch(r"\.output\.json\.[0-9a-f]{32}\.tmp", Path(target).name))
            if writing and is_temp and flags & os.O_EXCL and flags & os.O_CREAT:
                temporary_paths.add(target)
            if writing:
                if target not in allowed_writes | temporary_paths or access != os.O_WRONLY:
                    deny("open:unapproved-write")
                report["writes"].append([phase, "<export-temp>" if is_temp else Path(path).name, mode])
            else:
                if target not in allowed_reads | temporary_paths:
                    deny("open:unapproved-read")
                report["reads"].append([phase, "<export-temp>" if is_temp else Path(path).name, mode])
        elif event == "os.rename":
            if key(args[0]) not in temporary_paths or key(args[1]) != key(output):
                deny("rename:unapproved-publication")
        elif event in {"os.listdir", "os.scandir", "glob.glob", "glob.glob/2",
                       "pathlib.Path.glob", "pathlib.Path.rglob", "os.walk", "os.fwalk"}:
            deny("scan:" + event)
        elif event == "import" and "check" in args[0].split("."):
            deny("import:check")
        elif event in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"}:
            deny("external:" + event)
        elif event == "exec" and Path(args[0].co_filename).name.casefold() == "check.py":
            deny("exec:check.py")

    original_import = builtins.__import__
    original_import_module = importlib.import_module

    def check_import(name):
        if active:
            report["imports"].append(name)
            if "check" in name.split("."):
                deny("import:check")

    def guarded_import(name, *args, **kwargs):
        check_import(name)
        return original_import(name, *args, **kwargs)

    def guarded_import_module(name, *args, **kwargs):
        check_import(name)
        return original_import_module(name, *args, **kwargs)

    def fixed_transport(endpoint, body, api_key, timeout):
        report["requests"].append(body.decode("utf-8"))
        return 200, {}, json.dumps({"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(FIXED_REPLY)}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8}}).encode("utf-8")

    sys.addaudithook(audit)
    try:
        with patch.object(builtins, "__import__", guarded_import), \
                patch.object(importlib, "import_module", guarded_import_module):
            modules = {}
            for name, source in sources.items():
                module = types.ModuleType(name)
                module.__file__ = str(PROJECT / (name + ".py"))
                sys.modules[name] = module
                modules[name] = module
                exec(source, module.__dict__)

            phase = "negative-control"
            decoy = folder / "answers" / "people.json"
            attacks = {
                "builtin_open": lambda: open(decoy, "rb"),
                "io_open": lambda: io.open(decoy, "rb"),
                "path_open": lambda: decoy.read_bytes(),
                "os_open": lambda: os.open(decoy, os.O_RDONLY),
                "extra_input": lambda: (folder / "extra.json").read_bytes(),
                "output_read": lambda: output.read_bytes(),
                "listdir": lambda: os.listdir(folder),
                "scandir": lambda: os.scandir(folder),
                "iterdir": lambda: list(folder.iterdir()),
                "glob": lambda: glob.glob(str(folder / "*.json")),
                "iglob": lambda: list(glob.iglob(str(folder / "**"), recursive=True)),
                "path_glob": lambda: list(folder.glob("*")),
                "rglob": lambda: list(folder.rglob("*")),
                "walk": lambda: list(os.walk(folder)),
                "import_check": lambda: __import__("check"),
                "importlib_check": lambda: importlib.import_module("check"),
                "cached_check": lambda: importlib.import_module("check"),
                "exec_check": lambda: exec(compile("pass", str(folder / "check.py"), "exec")),
            }
            if attack == "cached_check":
                sys.modules["check"] = types.ModuleType("check")
            if attack in attacks:
                # Deliberately swallow the exception: the recorded violation
                # must still make the probe fail (as in broad runtime handlers).
                try:
                    attacks[attack]()
                except AssertionError:
                    pass

            phase = "loader"
            data = modules["data"].load_input(folder)
            data.require_complete()
            windows = modules["data"].build_windows(data)
            windows.require_complete()
            # Test contract only; no production prompt/extractor is introduced.
            payload = {"chats": [r.original for r in data.chat_records],
                       "messages": [r.original for r in data.message_records],
                       "seed": data.seed,
                       "windows": [dataclasses.asdict(w) for w in windows.windows]}
            phase = "model"
            os.chdir(folder)
            with patch.dict(os.environ, {"LLM_BASE_URL": "https://example.invalid/v1",
                                         "LLM_MODEL": "synthetic-model",
                                         "LLM_API_KEY": "synthetic-not-a-credential"}):
                modules["llm"]._default_client = modules["llm"].Client(
                    transport=fixed_transport, clock=lambda: 0.0)
                report["model_output"] = modules["llm"].chat(
                    [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                    temperature=0, max_tokens=64, response_format={"type": "json_object"})
                report["usage"] = modules["llm"]._default_client.budget.summary()
            phase = "solution"
            # The old naive producer is test-only now: Stage C must not report
            # unimplemented inference as successful empty goals/loops. Patch
            # only assembly; real loading, validation and export remain guarded.
            def synthetic_output(data, **kwargs):
                organisations, ties = [], []
                for record in data.chats_by_id.values():
                    chat = record.original
                    if chat["is_group"]:
                        identifier = "org_" + chat["chat_id"]
                        organisations.append({"id": identifier, "name": chat["name"],
                                              "type": "other", "side": "work", "role": "member"})
                        ties.append({"chat_id": chat["chat_id"], "organisation": identifier})
                    else:
                        ties.append({"chat_id": chat["chat_id"], "person": next(
                            p for p in chat["participants"] if p != "ME")})
                return {"people": [{"id": p, "circle": "friend"} for p in data.person_ids],
                        "organisations": organisations, "chats": ties, "goals": [], "open_loops": []}
            with patch.object(modules["solution"], "assemble_output", synthetic_output):
                if modules["solution"].main(str(folder), str(output)) != 0:
                    raise AssertionError("Synthetic pipeline failed")
            report["ok"] = not report["violations"]
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    finally:
        active = False
    if report["ok"]:
        report["output"] = output.read_bytes().hex()
    return report


class NoAnswerBoundaryTests(unittest.TestCase):
    def setUp(self):
        # Inherit workspace permissions, as Stage A does. Cleanup only this
        # newly created, explicitly owned directory after the child exits.
        self.folder = PROJECT / "tests" / ("stage-b-" + uuid.uuid4().hex)
        self.folder.mkdir()
        self.addCleanup(shutil.rmtree, self.folder)
        chats = [{"chat_id": "C1", "name": "Synthetic group", "is_group": True,
                  "participants": ["ME", "P1"]},
                 {"chat_id": "C2", "name": "Synthetic direct", "is_group": False,
                  "participants": ["ME", "P2"]}]
        messages = [{"id": "M1", "chat_id": "C1", "sender_id": "P1",
                     "sender_name": "Synthetic person", "ts": 100, "kind": "text",
                     "body": "Synthetic message नमस्ते", "quoted_id": None}]
        for name, rows in (("chats.jsonl", chats), ("messages.jsonl", messages)):
            (self.folder / name).write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        (self.folder / "seed.json").write_text('{"circles": {"P1": "family"}}', encoding="utf-8")

    def add_decoys(self):
        answers = self.folder / "answers"
        answers.mkdir()
        for name in ("people", "organisations", "chats", "goals", "open_loops"):
            (answers / (name + ".json")).write_text(json.dumps({"decoy": DECOY}), encoding="utf-8")
        (self.folder / "extra.json").write_text(DECOY, encoding="utf-8")
        (self.folder / "check.py").write_text("raise AssertionError('synthetic checker executed')\n", encoding="utf-8")

    def run_probe(self, attack=""):
        # Give each run the same initial artifact state. Client usage is run-local.
        for name in ("output.json", "usage.jsonl"):
            (self.folder / name).unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--probe", str(self.folder), attack],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def assert_clean(self, result):
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["violations"], [])
        # Path.open() can also emit a low-level os.open event with mode=None.
        self.assertEqual(Counter(name for phase, name, mode in result["reads"]
                                 if phase == "loader" and mode is not None),
                         Counter(INPUTS))
        self.assertEqual(set(name for _, name, _ in result["reads"]),
                         set(INPUTS) | {"schema.json", "<export-temp>"})
        self.assertEqual([[phase, name] for phase, name, mode in result["writes"]
                          if mode is not None], [["solution", "<export-temp>"]])
        self.assertFalse(any("check" in name.split(".") for name in result["imports"]))

    def test_inference_reads_only_allowed_files_without_scans(self):
        self.add_decoys()
        result = self.run_probe()
        self.assert_clean(result)
        self.assertEqual([name for phase, name, mode in result["reads"]
                          if phase == "solution" and mode is not None],
                         ["chats.jsonl", "messages.jsonl", "seed.json", "schema.json", "<export-temp>"])

    def test_requests_and_final_outputs_are_identical_with_and_without_decoys(self):
        before = self.run_probe()
        self.add_decoys()
        after = self.run_probe()
        for result in (before, after):
            self.assert_clean(result)
            self.assertEqual(len(result["requests"]), 1)  # Not an empty-payload comparison.
            body = json.loads(result["requests"][0])
            content = json.loads(body["messages"][0]["content"])
            self.assertEqual(content["seed"], {"circles": {"P1": "family"}})
            self.assertEqual(content["messages"][0]["id"], "M1")
            self.assertTrue(content["windows"])
            self.assertEqual(json.loads(result["model_output"]), FIXED_REPLY)
            final = json.loads(bytes.fromhex(result["output"]))
            self.assertEqual([p["id"] for p in final["people"]], ["P1", "P2"])
            self.assertEqual(len(final["chats"]), 2)
            self.assertNotIn(DECOY, json.dumps(result))
        for field in ("requests", "model_output", "output", "usage"):
            self.assertEqual(before[field], after[field], field)

    def test_allowed_input_change_affects_requests_and_output(self):
        before = self.run_probe()
        path = self.folder / "chats.jsonl"
        path.write_text(path.read_text(encoding="utf-8").replace('"P2"', '"P3"'), encoding="utf-8")
        after = self.run_probe()
        self.assert_clean(before)
        self.assert_clean(after)
        self.assertNotEqual(before["requests"], after["requests"])
        self.assertNotEqual(before["output"], after["output"])
        self.assertEqual(before["model_output"], after["model_output"])

    def test_guard_rejects_unapproved_opens_even_when_caught(self):
        self.add_decoys()
        for attack in ("builtin_open", "io_open", "path_open", "os_open", "extra_input", "output_read"):
            with self.subTest(attack=attack):
                result = self.run_probe(attack)
                self.assertFalse(result["ok"])
                self.assertEqual(result["violations"], ["open:unapproved-read"])

    def test_guard_rejects_directory_discovery_even_when_caught(self):
        self.add_decoys()
        for attack in ("listdir", "scandir", "iterdir", "glob", "iglob", "path_glob", "rglob", "walk"):
            with self.subTest(attack=attack):
                result = self.run_probe(attack)
                self.assertFalse(result["ok"])
                self.assertEqual(len(result["violations"]), 1)
                self.assertTrue(result["violations"][0].startswith("scan:"))

    def test_inference_never_imports_checker_including_initialization(self):
        self.add_decoys()
        self.assert_clean(self.run_probe())
        for attack in ("import_init", "import_check", "importlib_check", "cached_check", "exec_check"):
            with self.subTest(attack=attack):
                result = self.run_probe(attack)
                self.assertFalse(result["ok"])
                self.assertEqual(result["violations"],
                                 ["exec:check.py" if attack == "exec_check" else "import:check"])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--probe":
        print(json.dumps(_probe(sys.argv[2], sys.argv[3]), ensure_ascii=True))
    else:
        unittest.main()
