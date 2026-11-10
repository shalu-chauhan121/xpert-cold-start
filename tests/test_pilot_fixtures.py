"""Session-04 offline tests for the synthetic pilot fixtures and mock pipeline.

No network, no credentials, no real model: the production pipeline runs
end-to-end on the `mock_responses` transport only.
"""
import json
import os
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "tests" / "pilot_fixtures"))

import data as data_module
import mock_responses
from llm import Budget, Client, Deadline
from solution import assemble_output

ENV = {"LLM_BASE_URL": "https://synthetic.invalid/v1/",
       "LLM_API_KEY": "synthetic-key", "LLM_MODEL": "synthetic-v1"}
PACK_DIR = PROJECT / "tests" / "pilot_fixtures"
PACKS = ("pilot_en", "pilot_hi", "pilot_bn", "pilot_hn")


def load(pack):
    return data_module.load_input(str(PACK_DIR / pack))


def run_pipeline(pack):
    dataset = load(pack)
    dataset.require_complete()
    summary = {}
    with patch.dict(os.environ, ENV):
        client = Client(transport=mock_responses.respond, budget=Budget(250000))
        deadline = Deadline(started=time.monotonic(), network=600,
                            exit_target=750, overall=780)
        output = assemble_output(dataset, client=client, deadline=deadline,
                                 summary=summary)
    return dataset, summary, output


class TestFixtures(unittest.TestCase):
    def test_inputs_load(self):
        for pack in PACKS:
            with self.subTest(pack=pack):
                dataset = load(pack)
                self.assertEqual(dataset.status, "succeeded")
                self.assertEqual(len(dataset.chats_by_id), 4)
                self.assertEqual(len(dataset.person_ids), 6)
                self.assertEqual(len(dataset.messages_by_id), 18)
                self.assertEqual(sorted(dataset.seed.get("circles")),
                                 ["P01", "P02", "P03"])
                self.assertEqual(dataset.seed.get("organisations"), ["HomeServe"])

    def test_full_coverage(self):
        counts = set()
        for pack in PACKS:
            with self.subTest(pack=pack):
                dataset = load(pack)
                plan = data_module.build_windows(dataset)
                plan.require_complete()
                coverage = plan.coverage
                counts.add(len(plan.windows))
                self.assertEqual(coverage["status"], "succeeded")
                self.assertEqual(coverage["fully_covered_messages"], 18)
                self.assertEqual(coverage["primary_span_count"], 19)
        # Long-body splitting behaves identically across language packs.
        self.assertEqual(len(counts), 1)

    def test_extraction_validate_passes(self):
        from reasoning import validate_extraction
        for pack in PACKS:
            with self.subTest(pack=pack):
                dataset = load(pack)
                plan = data_module.build_windows(dataset)
                for window in plan.windows:
                    text = json.dumps(mock_responses.extraction_response(
                        (json.loads(json.dumps(
                            __import__("reasoning").window_packet(dataset, window))))),
                        ensure_ascii=False)
                    validate_extraction(text, dataset, window)


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.datasets, cls.summaries, cls.outputs = {}, {}, {}
        for pack in PACKS:
            dataset, summary, output = run_pipeline(pack)
            cls.datasets[pack], cls.summaries[pack], cls.outputs[pack] = \
                dataset, summary, output

    def test_all_packs_succeed(self):
        for pack in PACKS:
            with self.subTest(pack=pack):
                summary = self.summaries[pack]
                self.assertEqual(summary["state"], "succeeded")
                for stage, report in summary["stages"].items():
                    self.assertIn(report["state"], ("succeeded", "succeeded_empty"),
                                  stage)
                usage = summary["usage"]
                self.assertEqual(usage["unknown_usage_attempts"], 0)
                self.assertFalse(usage["over_ceiling"])
                # Observed offline usage stays inside the 250k reservation.
                self.assertLess(usage["charged_tokens"], 250000)

    def test_entities_and_organisations(self):
        for pack in PACKS:
            with self.subTest(pack=pack):
                output = self.outputs[pack]
                self.assertEqual(len(output["organisations"]), 1)
                org = output["organisations"][0]
                self.assertEqual(org["type"], "company")
                people = {p["id"]: p for p in output["people"]}
                self.assertEqual(set(people),
                                 {"P01", "P02", "P03", "P04", "P05", "P06"})
                self.assertEqual(people["P02"]["links"],
                                 [{"organisation": org["id"], "link": "supports"}])
                self.assertEqual(people["P02"]["looks_after"], ["P01"])
                chats = {c["chat_id"]: c for c in output["chats"]}
                self.assertEqual(chats["C_MAIN"], {"chat_id": "C_MAIN", "person": "P01"})
                self.assertEqual(chats["C_PAIR"], {"chat_id": "C_PAIR", "person": "P06"})
                self.assertEqual(chats["C_QUOTE"], {"chat_id": "C_QUOTE", "person": "P05"})
                self.assertEqual(chats["C_ORG"], {"chat_id": "C_ORG",
                                                  "organisation": org["id"]})

    def test_goals_single_supported(self):
        for pack in PACKS:
            with self.subTest(pack=pack):
                output = self.outputs[pack]
                self.assertEqual(len(output["goals"]), 1)
                goal = output["goals"][0]
                self.assertEqual(goal["title"], "Run a half marathon in January")
                self.assertEqual(goal["evidence"], ["M10", "M11"])
                rejected = self.summaries[pack]["stages"]["goals"]["rejected"]
                forwarded = [row for row in rejected if row["reason"] == "other_person"]
                self.assertEqual(len(forwarded), 1)  # the M12 forward obs

    def test_open_loops_semantics(self):
        expected = [
            ("send signed lease copy", "open", "P01", "M1", None),
            ("confirm tuition trial appointment", "open", "P02", "M3", "2026-09-23"),
            ("coordinate school pickup rota", "open", "P01", "M5", None),
            ("submit tuition reimbursement form", "open", "P03", "M7", None),
            ("suggest anniversary caterers", "open", "P01", "M13", None),
            ("book dentist appointment", "done", "ME", "M15", "2026-09-24"),
        ]
        for pack in PACKS:
            with self.subTest(pack=pack):
                loops = self.outputs[pack]["open_loops"]
                self.assertEqual(len(loops), len(expected))
                actual = sorted((item["title"], item["status"], item["owner"],
                                 item["source_msg"]) for item in loops)
                self.assertEqual(actual,
                                 sorted((t[0], t[1], t[2], t[3]) for t in expected))
                by_title = {item["title"]: item for item in loops}
                # Acknowledgement is not completion: the lease loop stays open.
                self.assertIsNone(by_title["send signed lease copy"].get("closed_by"))
                reopened = by_title["submit tuition reimbursement form"]
                self.assertIsNone(reopened.get("closed_by"))  # complete then reopen
                # Cross-chat completion via the quoted follow-up.
                self.assertEqual(by_title["book dentist appointment"]["closed_by"], "M16")
                self.assertEqual({item["owner"] for item in loops},
                                 {"P01", "P02", "P03", "ME"})


    def test_evidence_integrity(self):
        for pack in PACKS:
            with self.subTest(pack=pack):
                dataset = self.datasets[pack]
                output = self.outputs[pack]
                # Every goal and closure message id must exist in the input.
                for goal in output["goals"]:
                    for mid in goal["evidence"]:
                        self.assertIn(mid, dataset.messages_by_id)
                for item in output["open_loops"]:
                    self.assertIn(item["source_msg"], dataset.messages_by_id)
                    if item.get("closed_by"):
                        self.assertIn(item["closed_by"], dataset.messages_by_id)

    def test_help_decisions(self):
        for pack in PACKS:
            with self.subTest(pack=pack):
                loops = {item["title"]: item for item in self.outputs[pack]["open_loops"]}
                remind = loops["send signed lease copy"]["help"]
                self.assertEqual(remind["action"], "remind")
                self.assertEqual(remind["remind_at"], "2026-09-26T09:00:00+05:30")
                # Reminder must be strictly after input as_of.
                stamp = datetime.fromisoformat(
                    remind["remind_at"].replace("Z", "+00:00"))
                seconds = (stamp - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()
                self.assertGreater(seconds, self.datasets[pack].as_of)
                assist = loops["coordinate school pickup rota"]["help"]
                self.assertEqual(assist["action"], "assist")
                self.assertTrue(assist["next_step"].strip())
                self.assertTrue(assist["needs_yes"])
                leave = loops["confirm tuition trial appointment"]["help"]
                for decision in ("confirm tuition trial appointment",
                                 "submit tuition reimbursement form",
                                 "suggest anniversary caterers"):
                    help_value = loops[decision]["help"]
                    self.assertEqual(help_value["action"], "leave")
                    self.assertTrue(help_value["reason"].strip())
                # Closed loops carry no help recommendation.
                self.assertNotIn("help", loops["book dentist appointment"])

    def test_ambiguous_resolution_recorded(self):
        for pack in PACKS:
            with self.subTest(pack=pack):
                unresolved = self.summaries[pack]["stages"]["tasks"]["unresolved"]
                self.assertEqual(len(unresolved), 1)
                self.assertEqual(unresolved[0]["event"]["source_msg"], "M14")
                self.assertEqual(unresolved[0]["reason"], "ambiguous_evidence")

    def test_deterministic_repeatable(self):
        dataset, summary, first = run_pipeline("pilot_en")
        dataset2, summary2, second = run_pipeline_structure("pilot_en")
        self.assertEqual(json.dumps(first, sort_keys=True),
                         json.dumps(second, sort_keys=True))

    def test_language_packs_agree(self):
        def normalize(output):
            cloned = json.loads(json.dumps(output))
            for org in cloned["organisations"]:
                org["id"] = "<<org>>"
                org["name"] = "<<surface>>"
            for person in cloned["people"]:
                for link in person.get("links", []):
                    link["organisation"] = "<<org>>"
            for chat in cloned["chats"]:
                if "organisation" in chat:
                    chat["organisation"] = "<<org>>"
            return cloned
        base = None
        for pack in PACKS:
            normalized = normalize(self.outputs[pack])
            if base is None:
                base = normalized
            else:
                self.assertEqual(base, normalized,
                                 "output structure differs across language packs")


def run_pipeline_structure(pack):
    dataset, summary, output = run_pipeline(pack)
    return dataset, summary, output


if __name__ == "__main__":
    unittest.main()
