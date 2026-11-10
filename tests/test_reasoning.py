"""Synthetic Stage E extraction milestone; no network or dataset access."""
import ast
import copy
import json
from dataclasses import asdict
from pathlib import Path
import unittest

from data import InputData, InputRecord, INPUT_FILES, build_windows
from reasoning import extract_windows, validate_extraction, ReasoningError


def fixture():
    data = InputData(seed={}, person_ids=("P1",),
                     files_read_complete={name: True for name in INPUT_FILES})
    chat = InputRecord("chats.jsonl", 1, b"", {"chat_id": "C1", "participants": ["ME", "P1"]})
    data.chat_records = [chat]
    data.chats_by_id = {"C1": chat}
    for i in range(2):
        source = {"id": "M" + str(i), "chat_id": "C1", "sender_id": "ME",
                  "body": "Walk daily", "ts": i + 1, "kind": "text", "quoted_id": None}
        record = InputRecord("messages.jsonl", i + 1, b"", source, True, i + 1)
        data.message_records.append(record)
        data.messages_by_id[source["id"]] = record
    data.messages_by_chat = {"C1": data.message_records}
    return data, build_windows(data, max_primary_spans=1)


def observation():
    return {"kind": "goal", "subjects": ["ME"], "meaning": "A proposed walking habit",
            "evidence": [{"message_id": "M0", "start": 0, "end": 10, "text": "Walk daily"}]}


class FakeClient:
    def __init__(self, replies):
        self.replies = iter(replies)

    def request(self, messages, **settings):
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        text = json.dumps(reply)
        settings["validate"](text)
        return text


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.data, self.plan = fixture()
        self.replies = [{"covered": [asdict(s) for s in w.primary],
                         "observations": [observation()]} for w in self.plan.windows]

    def test_overlap_retains_both_window_provenances(self):
        result = extract_windows(self.data, self.plan, FakeClient(self.replies))
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(len(result["observations"]), 1)
        self.assertEqual(len(result["observations"][0]["windows"]), 2)
        self.assertEqual(result["completed"], result["required"])

    def test_unknown_ids_wrong_text_and_out_of_scope_spans_rejected(self):
        for update in ({"message_id": "invented"}, {"text": "fabricated"},
                       {"end": 99}, {"message_id": "M1"}):
            reply = copy.deepcopy(self.replies[0])
            reply["observations"][0]["evidence"][0].update(update)
            with self.subTest(update=update), self.assertRaises(ReasoningError):
                validate_extraction(json.dumps(reply), self.data, self.plan.windows[0])

    def test_partial_primary_acknowledgement_is_incomplete(self):
        self.replies[0]["covered"] = []
        result = extract_windows(self.data, self.plan, FakeClient(self.replies))
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(len(result["completed"]), 1)

    def test_timeout_never_becomes_empty_success(self):
        result = extract_windows(self.data, self.plan, FakeClient([TimeoutError(), TimeoutError()]))
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(len(result["failures"]), 2)

    def test_completed_empty_is_distinct(self):
        for reply in self.replies:
            reply["observations"] = []
        result = extract_windows(self.data, self.plan, FakeClient(self.replies))
        self.assertEqual(result["state"], "succeeded_empty")
        self.assertEqual(result["completed"], result["required"])

    def test_distinct_meanings_are_not_merged_by_source(self):
        self.replies[1]["observations"][0]["meaning"] = "Another proposed intention"
        result = extract_windows(self.data, self.plan, FakeClient(self.replies))
        self.assertEqual(len(result["observations"]), 2)

    def test_task_updates_preserved_without_replay(self):
        for reply in self.replies:
            reply["observations"][0]["kind"] = "task_update"
        result = extract_windows(self.data, self.plan, FakeClient(self.replies))
        self.assertEqual(result["observations"][0]["kind"], "task_update")
        self.assertNotIn("status", result["observations"][0])

    def test_original_records_unchanged_and_python39_grammar(self):
        before = copy.deepcopy(self.data)
        extract_windows(self.data, self.plan, FakeClient(self.replies))
        self.assertEqual(self.data, before)
        ast.parse((Path(__file__).resolve().parents[1] / "reasoning.py").read_text(),
                  feature_version=(3, 9))
