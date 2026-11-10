"""Stage G production entry-point tests with synthetic HTTP responses."""
import ast
import builtins
import copy
import io
import json
import os
from pathlib import Path
import shutil
import socket
import unittest
import uuid
from unittest.mock import patch

import solution
from llm import Client, Budget, Deadline
from test_llm import Clock, response


class PipelineTransport:
    def __init__(self, action="leave", fail=None, closed=False):
        self.action, self.fail, self.closed = action, fail, closed
        self.requests = []

    def __call__(self, endpoint, wire, key, timeout):
        body = json.loads(wire)
        packet = json.loads(body["messages"][1]["content"])
        self.requests.append(copy.deepcopy(body))
        system = body["messages"][0]["content"]
        if "Extract observations" in system:
            observations = []
            for span in packet["primary"]:
                if span["message_id"] != "M1":
                    continue
                evidence = {k: span[k] for k in ("message_id", "start", "end", "text")}
                for kind in ("person", "organisation", "goal", "task_create"):
                    observations.append({"kind": kind, "subjects": ["ME", "P1"],
                                         "meaning": "Synthetic " + kind, "evidence": [evidence]})
            if self.closed:
                for span in packet["primary"]:
                    if span["message_id"] == "M2":
                        observations.append({"kind": "task_update", "subjects": ["ME"], "meaning": "Completed",
                                             "evidence": [{k: span[k] for k in ("message_id", "start", "end", "text")}]})
            answer = {"covered": [{k: s[k] for k in ("message_id", "start", "end")} for s in packet["primary"]],
                      "observations": observations}
            stage = "extraction"
        elif "Consider seed organisation" in packet.get("contract", ""):
            answer = {"groups": [{"members": [o["id"] for o in packet["observations"]],
                                   "record": {"name": "Synthetic company", "type": "company", "side": "work", "role": "owner"},
                                   "aliases": []}], "rejected": [], "pending": []}
            stage = "organisations"
        elif "decisions:[{category" in packet.get("contract", ""):
            evidence = [packet["observations"][0]["id"]]
            answer = {"decisions": []}
            for category, identifier in packet["required"]:
                record = ({"id": identifier, "circle": "colleague"} if category == "people" else
                          {"chat_id": identifier, "organisation": packet["organisations"][0]["id"]})
                answer["decisions"].append({"category": category, "id": identifier, "record": record, "evidence": evidence})
            stage = "entities"
        elif "support:[{span" in packet.get("contract", ""):
            obs = packet["observations"][0]
            answer = {"groups": [{"members": [obs["id"]], "record": {"title": "Practice writing", "area": "work", "type": "habit", "horizon": "1yr"},
                                  "support": [{"span": obs["evidence"][0], "role": "explicit", "episode": "one", "antecedent": None}]}],
                      "pending": [], "rejected": []}
            stage = "goals"
        elif packet.get("phase") == "interpret":
            mid = packet["observation"]["evidence"][0]["message_id"]
            answer = {"operation": "create" if mid == "M1" else "complete", "source_msg": mid, "evidence": [mid],
                      "details": {"action": "Draft", "object": "report", "type": "commitment", "owner": "ME", "due": None} if mid == "M1" else {}}
            stage = "tasks"
        elif packet.get("phase") == "match":
            answer = {"decision": "match", "target": packet["candidates"][0]["id"], "evidence": ["M1", "M2"]}
            stage = "tasks"
        else:
            help_value = {"leave": {"action": "leave", "reason": "Awaiting the user's work"},
                          "assist": {"action": "assist", "next_step": "Draft an outline", "needs_yes": True},
                          "remind": {"action": "remind", "remind_at": "2030-01-01T09:00:00+00:00"}}[self.action]
            answer = {"decisions": [{"id": tid, "help": help_value, "evidence": ["M1"]} for tid in packet["required"]]}
            stage = "help"
        if stage == self.fail:
            return 200, {}, b"{}"
        return response(json.dumps(answer))


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(__file__).resolve().parent / ("stage-g-" + uuid.uuid4().hex)
        self.folder.mkdir()
        self.addCleanup(shutil.rmtree, self.folder)
        self.output = self.folder / "output.json"
        self.output.write_text("old output", encoding="utf-8")
        chats = [{"chat_id": "C1", "is_group": True, "name": "Synthetic company", "participants": ["ME", "P1"]}]
        messages = [{"id": "M" + str(i), "chat_id": "C1", "sender_id": "ME", "sender_name": "User", "ts": i,
                     "kind": "text", "body": text, "quoted_id": None} for i, text in
                    ((1, "I own Synthetic company, P1 is a colleague. I aim to practice writing. I will draft a report."),
                     (2, "The report is done."))]
        for name, rows in (("chats.jsonl", chats), ("messages.jsonl", messages)):
            (self.folder / name).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        (self.folder / "seed.json").write_text('{"circles":{"P1":"colleague"}}', encoding="utf-8")
        self.clock = Clock()

    def run_pipeline(self, transport, deadline=None):
        deadline = deadline or Deadline(self.clock)
        client = Client(transport=transport, clock=self.clock, sleep=self.clock.sleep,
                        deadline=deadline, budget=Budget(planned_base_calls=30))
        summary = {}
        allowed = {(self.folder / name).absolute() for name in ("chats.jsonl", "messages.jsonl", "seed.json")}
        allowed.add(Path(solution.__file__).resolve().with_name("schema.json"))
        real_open, real_io_open = builtins.open, io.open
        def guarded_open(original):
            def checked(path, mode="r", *args, **kwargs):
                target = Path(path).absolute()
                temporary = target.parent == self.folder and target.name.startswith(".output.json.") and target.suffix == ".tmp"
                if any(flag in mode for flag in "wax+"):
                    self.assertTrue(temporary, "Unapproved pipeline write")
                else:
                    self.assertTrue(target in allowed or temporary, "Unapproved pipeline read")
                return original(path, mode, *args, **kwargs)
            return checked
        with patch.dict(os.environ, {"LLM_BASE_URL": "https://synthetic.invalid", "LLM_MODEL": "synthetic", "LLM_API_KEY": "synthetic"}), \
                patch.object(builtins, "open", guarded_open(real_open)), \
                patch.object(io, "open", guarded_open(real_io_open)), \
                patch.object(os, "listdir", side_effect=AssertionError("Directory scans forbidden")), \
                patch.object(os, "scandir", side_effect=AssertionError("Directory scans forbidden")), \
                patch.object(socket, "getaddrinfo", side_effect=AssertionError("Network forbidden")), \
                patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")), \
                patch("sys.stderr", new_callable=io.StringIO):
            status = solution.main(self.folder, self.output, client=client, deadline=deadline, summary=summary)
        return status, summary

    def test_all_categories_and_all_help_actions(self):
        for action in ("assist", "remind", "leave"):
            with self.subTest(action=action):
                status, summary = self.run_pipeline(PipelineTransport(action))
                self.assertEqual(status, 0, summary)
                output = json.loads(self.output.read_text())
                self.assertEqual(set(output), {"people", "organisations", "chats", "goals", "open_loops"})
                self.assertTrue(all(output.values()))
                self.assertEqual(output["open_loops"][0]["help"]["action"], action)
                self.assertEqual(output["people"][0]["circle"], "colleague")
                self.assertEqual(summary["state"], "succeeded")

    def test_each_stage_failure_preserves_old_output(self):
        for stage in ("extraction", "organisations", "entities", "goals", "tasks", "help"):
            with self.subTest(stage=stage):
                status, summary = self.run_pipeline(PipelineTransport(fail=stage))
                self.assertEqual(status, 1)
                self.assertEqual(summary["state"], "incomplete")
                self.assertEqual(self.output.read_text(), "old output")

    def test_closed_task_retained_without_help(self):
        status, summary = self.run_pipeline(PipelineTransport(closed=True))
        self.assertEqual(status, 0, summary)
        task = json.loads(self.output.read_text())["open_loops"][0]
        self.assertEqual((task["status"], task["closed_by"]), ("done", "M2"))
        self.assertNotIn("help", task)
        self.assertEqual(summary["stages"]["help"]["state"], "succeeded_empty")

    def test_actual_entry_requests_and_output_ignore_decoys(self):
        first = PipelineTransport()
        self.assertEqual(self.run_pipeline(first)[0], 0)
        original = self.output.read_bytes()
        decoy = self.folder / "answers"
        decoy.mkdir()
        (decoy / "people.json").write_text('"synthetic decoy"')
        second = PipelineTransport()
        self.assertEqual(self.run_pipeline(second)[0], 0)
        self.assertEqual(first.requests, second.requests)
        self.assertEqual(self.output.read_bytes(), original)
        self.assertEqual(self.run_pipeline(PipelineTransport("assist"))[0], 0)
        self.assertNotEqual(self.output.read_bytes(), original)

    def test_display_name_renaming_preserves_ids_and_deterministic_output(self):
        original = PipelineTransport()
        self.assertEqual(self.run_pipeline(original)[0], 0)
        expected = self.output.read_bytes()
        for filename, field in (("chats.jsonl", "name"), ("messages.jsonl", "sender_name")):
            path = self.folder / filename
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for row in rows:
                row[field] = "Renamed synthetic display name"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        renamed = PipelineTransport()
        self.assertEqual(self.run_pipeline(renamed)[0], 0)
        self.assertEqual(self.output.read_bytes(), expected)
        self.assertNotEqual(renamed.requests, original.requests)
        replay = PipelineTransport()
        self.assertEqual(self.run_pipeline(replay)[0], 0)
        self.assertEqual(replay.requests, renamed.requests)
        self.assertEqual(self.output.read_bytes(), expected)

    def test_deadlines_prevent_dispatch_and_publication(self):
        deadline = Deadline(self.clock, started=0)
        self.clock.now = 1620
        transport = PipelineTransport()
        self.assertEqual(self.run_pipeline(transport, deadline)[0], 1)
        self.assertEqual(transport.requests, [])
        self.assertEqual(self.output.read_text(), "old output")
        self.clock.now = 1770
        self.assertEqual(self.run_pipeline(transport, deadline)[0], 1)

    def test_exit_deadline_rechecked_before_atomic_replace(self):
        from data import load_input
        data = load_input(self.folder)
        transport = PipelineTransport()
        client = Client(transport=transport, clock=self.clock)
        with patch.dict(os.environ, {"LLM_BASE_URL": "https://synthetic.invalid", "LLM_MODEL": "synthetic", "LLM_API_KEY": "synthetic"}):
            output = solution.assemble_output(data, client=client)
        deadline = Deadline(self.clock, started=0)
        real_validate = solution.validate_output
        calls = []
        def validate(*args):
            real_validate(*args)
            calls.append(1)
            if len(calls) == 2:
                self.clock.now = 1770
        with patch.object(solution, "validate_output", side_effect=validate), self.assertRaises(Exception):
            solution.export_output(output, data, self.output, deadline)
        self.assertEqual(self.output.read_text(), "old output")
        self.assertEqual(list(self.folder.glob(".output.json.*.tmp")), [])

    def test_python39_syntax_and_launcher_constants(self):
        project = Path(__file__).resolve().parents[1]
        ast.parse((project / "solution.py").read_text(), feature_version=(3, 9))
        launcher = (project / "run.sh").read_text()
        self.assertIn("--kill-after=2s 1770s", launcher)
        self.assertNotIn("--foreground", launcher)

    def test_model_timeout_never_publishes_empty_success(self):
        def timeout(*args):
            raise TimeoutError("synthetic")
        status, summary = self.run_pipeline(timeout)
        self.assertEqual(status, 1)
        self.assertEqual(summary["state"], "incomplete")
        self.assertEqual(self.output.read_text(), "old output")
        self.assertGreater(summary["usage"]["unknown_usage_attempts"], 0)

    def test_invalid_reminder_preserves_output(self):
        base = PipelineTransport("remind")
        def invalid(*args):
            status, headers, raw = base(*args)
            return status, headers, raw.replace(b"2030-01-01T09:00:00+00:00", b"1970-01-01T00:00:00+00:00")
        status, summary = self.run_pipeline(invalid)
        self.assertEqual(status, 1)
        self.assertEqual(summary["stages"]["help"]["state"], "incomplete")
        self.assertEqual(self.output.read_text(), "old output")
