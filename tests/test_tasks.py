"""Stage F synthetic accepted semantics; no API, checker or dataset access."""
import ast
import copy
from pathlib import Path
import unittest
from data import InputData, InputRecord, INPUT_FILES
from tasks import build_ledger, replay
from reasoning import review_task_packet
from test_reasoning import FakeClient


class LedgerTests(unittest.TestCase):
    def fixture(self, operations):
        data = InputData(seed={}, person_ids=("P1", "P2"),
                         files_read_complete={f: True for f in INPUT_FILES})
        for cid in ("A", "B"):
            record = InputRecord("chats.jsonl", 1, b"", {"chat_id": cid, "participants": ["ME", "P1"]})
            data.chats_by_id[cid] = record
            data.chat_records.append(record)
        observations, decisions = [], {}
        for index, operation in enumerate(operations):
            mid = "M" + str(index)
            body = "Synthetic draft " + str(index)
            source = {"id": mid, "chat_id": "A", "sender_id": "P1", "body": body,
                      "ts": index + 1, "kind": "text", "quoted_id": None}
            record = InputRecord("messages.jsonl", index + 1, b"", source, True, index + 1)
            data.messages_by_id[mid] = record
            data.message_records.append(record)
            observations.append({"id": "O" + str(index), "kind": "task_create" if operation == "create" else "task_update",
                                 "subjects": ["P1"], "meaning": "Synthetic " + operation,
                                 "evidence": [{"message_id": mid, "start": 0, "end": len(body), "text": body}],
                                 "windows": ["W" + str(index)]})
            details = ({"action": "Send", "object": "draft", "owner": "P1", "type": "commitment", "due": None}
                       if operation == "create" else {"owner": "P2"} if operation == "update" else {})
            decisions[mid] = {"operation": operation, "source_msg": mid, "evidence": [mid], "details": details}
        extraction = {"state": "succeeded", "required": ["w"], "completed": ["w"], "failures": [], "observations": observations}
        return data, extraction, decisions

    def reviewer(self, decisions, match=None):
        def review(packet, validate):
            if packet["phase"] == "interpret":
                mid = packet["observation"]["evidence"][0]["message_id"]
                value = decisions[mid]
                if isinstance(value, Exception):
                    raise value
                reply = copy.deepcopy(value)
            elif match:
                reply = match(packet)
            else:
                event = packet["event"]
                target = packet["candidates"][0]
                matched = event["operation"] != "create"
                reply = {"decision": "match" if matched else "none", "target": target["id"] if matched else None,
                         "evidence": sorted({event["source_msg"], target["source_msg"]})}
            validate(reply)
            return reply
        return review

    def run_ops(self, operations):
        data, extraction, decisions = self.fixture(operations)
        return build_ledger(data, extraction, self.reviewer(decisions))

    def test_acknowledgement_does_not_close_then_completion_does(self):
        self.assertEqual(self.run_ops(["create", "acknowledge"])["tasks"][0]["status"], "open")
        task = self.run_ops(["create", "acknowledge", "complete"])["tasks"][0]
        self.assertEqual((task["status"], task["closed_by"], task["source_msg"]), ("done", "M2", "M0"))

    def test_cancel_and_negated_cancellation(self):
        self.assertEqual(self.run_ops(["create", "cancel"])["tasks"][0]["status"], "dropped")
        # Interpretation of negation is supplied, not inferred by replay keywords.
        self.assertEqual(self.run_ops(["create", "acknowledge"])["tasks"][0]["status"], "open")

    def test_reopen_clears_closure_but_keeps_history(self):
        for closure in ("complete", "cancel"):
            task = self.run_ops(["create", closure, "reopen"])["tasks"][0]
            self.assertEqual(task["status"], "open")
            self.assertIsNone(task["closed_by"])
            self.assertEqual(task["events"][1]["operation"], closure)

    def test_reassignment_does_not_close(self):
        task = self.run_ops(["create", "update"])["tasks"][0]
        self.assertEqual((task["owner"], task["status"]), ("P2", "open"))
        self.assertEqual(task["owner_evidence"], ["M1"])

    def test_replay_restarts_from_origin_after_reassignment(self):
        data, extraction, decisions = self.fixture(["create", "update", "complete"])
        task = build_ledger(data, extraction, self.reviewer(decisions))["tasks"][0]
        self.assertEqual(replay(task, data), task)

    def test_new_deliverable_after_completion_stays_separate(self):
        result = self.run_ops(["create", "complete", "create"])
        self.assertEqual(len(result["tasks"]), 2)
        self.assertEqual(sorted(t["status"] for t in result["tasks"]), ["done", "open"])

    def test_permutation_and_late_completion_replay(self):
        data, extraction, decisions = self.fixture(["create", "complete", "reopen"])
        first = build_ledger(data, extraction, self.reviewer(decisions))
        extraction["observations"].reverse()
        self.assertEqual(build_ledger(data, extraction, self.reviewer(decisions)), first)
        task = copy.deepcopy(first["tasks"][0])
        task["events"].reverse()
        self.assertEqual(replay(task, data)["status"], "open")

    def test_duplicate_overlap_retains_provenance(self):
        data, extraction, decisions = self.fixture(["create"])
        duplicate = copy.deepcopy(extraction["observations"][0])
        duplicate.update(id="duplicate", windows=["another-window"])
        extraction["observations"].append(duplicate)
        result = build_ledger(data, extraction, self.reviewer(decisions))
        self.assertEqual(len(result["tasks"]), 1)
        self.assertEqual(result["tasks"][0]["events"][0]["provenance"]["extraction_ids"], ["O0", "duplicate"])
        self.assertEqual(len(result["tasks"][0]["events"][0]["provenance"]["windows"]), 2)

    def test_two_tasks_same_message_not_merged_by_source(self):
        data, extraction, decisions = self.fixture(["create", "create"])
        extraction["observations"][1]["evidence"] = copy.deepcopy(extraction["observations"][0]["evidence"])
        extraction["observations"][1]["meaning"] = "Separate report"
        base = self.reviewer(decisions)
        def review(packet, validate):
            if packet["phase"] == "interpret" and packet["observation"]["meaning"] == "Separate report":
                event = copy.deepcopy(decisions["M0"])
                event["details"]["object"] = "report"
                validate(event)
                return event
            return base(packet, validate)
        result = build_ledger(data, extraction, review)
        self.assertEqual(len(result["tasks"]), 2)
        self.assertEqual({t["source_msg"] for t in result["tasks"]}, {"M0"})

    def test_cross_chat_closure_preserves_origin(self):
        data, extraction, decisions = self.fixture(["create", "complete"])
        data.messages_by_id["M1"].original.update(chat_id="B", quoted_id="M0")
        task = build_ledger(data, extraction, self.reviewer(decisions))["tasks"][0]
        self.assertEqual((task["chat_id"], task["source_msg"], task["closed_by"]), ("A", "M0", "M1"))

    def test_unrelated_cross_chat_does_not_match_on_me_alone(self):
        data, extraction, decisions = self.fixture(["create", "complete"])
        data.messages_by_id["M1"].original["chat_id"] = "B"
        data.chats_by_id["B"].original["participants"] = ["ME", "P2"]
        result = build_ledger(data, extraction, self.reviewer(decisions))
        self.assertEqual(result["tasks"][0]["status"], "open")
        self.assertEqual(result["unresolved"][0]["reason"], "unmatched_after_review")

    def test_reviewed_ambiguity_preserves_last_state(self):
        result = self.run_ops(["create", "ambiguous"])
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(result["tasks"][0]["status"], "open")
        self.assertEqual(result["unresolved"][0]["reason"], "ambiguous_evidence")

    def test_simultaneous_conflicting_events_remain_incomplete(self):
        data, extraction, decisions = self.fixture(["create", "complete", "cancel"])
        data.messages_by_id["M2"].timestamp = 2
        result = build_ledger(data, extraction, self.reviewer(decisions))
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["tasks"][0]["status"], "open")
        self.assertEqual(len(result["tasks"][0]["conflicts"]), 2)
        self.assertIsNone(result["tasks"][0]["closed_by"])
        self.assertEqual(replay(result["tasks"][0], data), result["tasks"][0])

    def simultaneous_closures(self, operation):
        data, extraction, decisions = self.fixture(["create", operation, operation])
        data.messages_by_id["M2"].timestamp = 2
        result = build_ledger(data, extraction, self.reviewer(decisions))
        task = result["tasks"][0]
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(task["status"], "done" if operation == "complete" else "dropped")
        self.assertIsNone(task["closed_by"])
        self.assertEqual(task["conflicts"], [e["id"] for e in task["events"] if e["operation"] == operation])
        self.assertEqual(task["evidence"], ["M0", "M1", "M2"])
        self.assertEqual(len(task["events"]), 3)
        self.assertEqual([e["provenance"]["extraction_ids"] for e in task["events"]], [["O0"], ["O1"], ["O2"]])
        return data, task

    def test_simultaneous_completions_have_ambiguous_closure(self):
        self.simultaneous_closures("complete")

    def test_simultaneous_cancellations_have_ambiguous_closure(self):
        self.simultaneous_closures("cancel")

    def test_simultaneous_closure_replay_is_deterministic(self):
        for operation in ("complete", "cancel"):
            with self.subTest(operation=operation):
                data, task = self.simultaneous_closures(operation)
                before = copy.deepcopy(task)
                self.assertEqual(replay(task, data), before)
                task["events"].reverse()
                self.assertEqual(replay(task, data), before)

    def test_duplicate_closure_event_is_not_distinct_ambiguity(self):
        data, extraction, decisions = self.fixture(["create", "complete"])
        duplicate = copy.deepcopy(extraction["observations"][-1])
        duplicate.update(id="paraphrase", meaning="Same closure phrased differently")
        extraction["observations"].append(duplicate)
        result = build_ledger(data, extraction, self.reviewer(decisions))
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(result["tasks"][0]["closed_by"], "M1")

    def test_closure_before_origin_is_conflict(self):
        data, extraction, decisions = self.fixture(["create", "complete"])
        data.messages_by_id["M1"].timestamp = 0
        result = build_ledger(data, extraction, self.reviewer(decisions))
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["tasks"][0]["status"], "open")

    def test_failed_interpretation_not_empty_success(self):
        data, extraction, decisions = self.fixture(["create"])
        decisions["M0"] = TimeoutError("private text")
        result = build_ledger(data, extraction, self.reviewer(decisions))
        self.assertEqual(result["state"], "incomplete")
        self.assertTrue(result["pending"])
        self.assertNotIn("private text", str(result))

    def test_empty_and_incomplete_extraction_distinct(self):
        data, extraction, decisions = self.fixture([])
        self.assertEqual(build_ledger(data, extraction, self.reviewer(decisions))["state"], "succeeded_empty")
        extraction["state"] = "incomplete"
        self.assertEqual(build_ledger(data, extraction, self.reviewer(decisions))["state"], "incomplete")

    def test_unknown_evidence_owner_and_undated_rejected(self):
        for field, value in (("owner", "unknown"), ("due", "2025-02-30")):
            data, extraction, decisions = self.fixture(["create"])
            decisions["M0"]["details"][field] = value
            self.assertEqual(build_ledger(data, extraction, self.reviewer(decisions))["state"], "incomplete")
        data, extraction, decisions = self.fixture(["create"])
        extraction["observations"][0]["evidence"][0]["text"] = "fabricated"
        self.assertEqual(build_ledger(data, extraction, self.reviewer(decisions))["state"], "incomplete")
        data, extraction, decisions = self.fixture(["create"])
        data.messages_by_id["M0"].timestamp = None
        self.assertEqual(build_ledger(data, extraction, self.reviewer(decisions))["state"], "incomplete")

    def test_candidate_partitions_exhaustive_and_failure_pending(self):
        data, extraction, decisions = self.fixture(["create", "create", "complete"])
        def match(packet):
            event, target = packet["event"], packet["candidates"][0]
            if event["operation"] == "complete" and target["source_msg"] == "M1":
                raise TimeoutError()
            return {"decision": "none", "target": None, "evidence": [event["source_msg"]]}
        result = build_ledger(data, extraction, self.reviewer(decisions, match), candidate_batch_size=1)
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(len(result["searches"]), 3)
        self.assertTrue(result["pending"])
        self.assertEqual({t["status"] for t in result["tasks"]}, {"open"})

    def test_budget_bound_and_no_source_mutation(self):
        data, extraction, decisions = self.fixture(["create"])
        before = copy.deepcopy((data, extraction))
        self.assertEqual(build_ledger(data, extraction, self.reviewer(decisions), max_packet_bytes=1)["state"], "incomplete")
        self.assertEqual((data, extraction), before)

    def test_reasoning_review_seam_and_python39(self):
        result = review_task_packet(FakeClient([{"accepted": True}]), {"synthetic": True},
                                    lambda r: self.assertEqual(r, {"accepted": True}))
        self.assertEqual(result, {"accepted": True})
        for name in ("tasks.py", "reasoning.py"):
            ast.parse((Path(__file__).resolve().parents[1] / name).read_text(), feature_version=(3, 9))

    def test_duplicate_semantic_creation_does_not_overwrite_provenance(self):
        data, extraction, decisions = self.fixture(["create"])
        second = copy.deepcopy(extraction["observations"][0])
        second.update(id="paraphrase", meaning="Same supported obligation paraphrased", windows=["other"])
        extraction["observations"].append(second)
        result = build_ledger(data, extraction, self.reviewer(decisions))
        self.assertEqual(len(result["tasks"]), 1)
        self.assertEqual(len(result["tasks"][0]["events"]), 2)
        self.assertEqual(result["state"], "succeeded")

    def test_duplicate_reopen_applies_once(self):
        data, extraction, decisions = self.fixture(["create", "complete", "reopen"])
        second = copy.deepcopy(extraction["observations"][-1])
        second.update(id="paraphrase", meaning="Same renewal paraphrased")
        extraction["observations"].append(second)
        result = build_ledger(data, extraction, self.reviewer(decisions))
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(result["tasks"][0]["status"], "open")

    def test_simultaneous_origin_and_closure_do_not_invent_order(self):
        data, extraction, decisions = self.fixture(["create", "complete"])
        data.messages_by_id["M1"].timestamp = 1
        result = build_ledger(data, extraction, self.reviewer(decisions))
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["tasks"][0]["status"], "open")
