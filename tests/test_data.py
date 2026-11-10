"""Synthetic Stage A tests. No challenge answer files or model calls are used."""

import copy
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from data import (MessageSpan, ProcessingWindow, WindowPlan, build_windows,
                  load_input, validate_window_coverage)  # noqa: E402


def chat(cid="C1", participants=None):
    return {"chat_id": cid, "name": "Synthetic chat", "is_group": True,
            "participants": participants if participants is not None else ["ME", "P1"]}


def message(mid="M1", cid="C1", sender="P1", ts=100):
    return {"id": mid, "chat_id": cid, "sender_id": sender, "sender_name": "Synthetic person",
            "ts": ts, "kind": "text", "body": "Original text", "quoted_id": None}


class InputTests(unittest.TestCase):
    def setUp(self):
        # Use inherited permissions; Python's private Windows temp directories can
        # exclude the sandbox identity. Each test owns only this new directory.
        self.folder = PROJECT / "tests" / ("stage-a-" + uuid.uuid4().hex)
        self.folder.mkdir()
        self.addCleanup(shutil.rmtree, self.folder)

    def write_inputs(self, chats=None, messages=None, seed=None):
        chats = [chat()] if chats is None else chats
        messages = [message()] if messages is None else messages
        seed = {} if seed is None else seed
        for filename, records in (("chats.jsonl", chats), ("messages.jsonl", messages)):
            (self.folder / filename).write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
        (self.folder / "seed.json").write_text(json.dumps(seed, ensure_ascii=False), encoding="utf-8")

    def codes(self, result):
        return [issue.code for issue in result.issues]

    def test_indexes_and_chronology_across_chats(self):
        records = [message("late", ts=300), message("other", "C2", "P2", 150),
                   message("early", ts=100), message("tie", ts=100)]
        self.write_inputs([chat(), chat("C2", ["ME", "P2", "P3"]), chat("C3")], records)
        result = load_input(self.folder)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual([r.original["id"] for r in result.messages_by_chat["C1"]], ["early", "tie", "late"])
        self.assertEqual([r.original["id"] for r in result.messages_by_chat["C2"]], ["other"])
        self.assertEqual(result.messages_by_chat["C3"], [])
        self.assertEqual(result.messages_by_sender["P3"], [])
        self.assertEqual(result.messages_by_sender["ME"], [])
        self.assertEqual(result.person_ids, ("P1", "P2", "P3"))
        self.assertIs(result.messages_by_id["early"], result.messages_by_chat["C1"][0])
        self.assertIs(result.messages_by_id["other"], result.messages_by_sender["P2"][0])
        self.assertEqual(result.as_of, 300)
        self.assertEqual(result.summary()["messages_indexed"], 4)
        result.require_complete()

    def test_original_ids_text_metadata_and_line_bytes_preserved(self):
        item = message("  M-001  ", "  C-001  ")
        item["body"] = "Hello\nनमस्ते, kal bhejunga. বাংলা 👋\n" + "long text " * 10000
        item["extra"] = {"unmodified": [1, "x", None]}
        before = copy.deepcopy(item)
        self.write_inputs([chat("  C-001  ")], [item], {"circles": {"P1": "friend"}})
        raw = (self.folder / "messages.jsonl").read_bytes()
        result = load_input(self.folder)
        evidence = result.evidence("  M-001  ")
        self.assertEqual(evidence.original, before)
        self.assertEqual(evidence.raw_bytes, raw)
        self.assertEqual((evidence.file, evidence.line), ("messages.jsonl", 1))
        self.assertIn("  C-001  ", result.chats_by_id)
        self.assertEqual(result.seed, {"circles": {"P1": "friend"}})
        self.assertEqual(json.loads(result.seed_raw_bytes), result.seed)
        with self.assertRaises(KeyError):
            result.evidence("fabricated")

    def test_blank_lines_count_physical_source_lines_not_messages(self):
        self.write_inputs()
        raw = b"\n \t\n" + (self.folder / "messages.jsonl").read_bytes() + b"\n"
        (self.folder / "messages.jsonl").write_bytes(raw)
        result = load_input(self.folder)
        self.assertEqual(result.summary()["message_lines_seen"], 1)
        self.assertEqual(result.evidence("M1").line, 3)

    def test_valid_empty_dataset_is_successful_empty(self):
        self.write_inputs([], [], {})
        result = load_input(self.folder)
        self.assertEqual(result.status, "succeeded_empty")
        self.assertEqual(result.summary()["messages_indexed"], 0)
        self.assertIsNone(result.as_of)
        self.assertEqual(result.issues, [])
        result.require_complete()

    def test_chat_without_messages_is_not_an_empty_dataset(self):
        self.write_inputs(messages=[])
        result = load_input(self.folder)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.messages_by_chat, {"C1": []})
        self.assertIsNone(result.as_of)

    def test_each_missing_required_file_fails_instead_of_looking_empty(self):
        for filename in ("chats.jsonl", "messages.jsonl", "seed.json"):
            with self.subTest(filename=filename):
                self.write_inputs([], [])
                (self.folder / filename).unlink()
                result = load_input(self.folder)
                self.assertEqual(result.status, "failed")
                self.assertFalse(result.files_read_complete[filename])
                with self.assertRaises(ValueError):
                    result.require_complete()

    def test_nonexistent_directory_fails_without_creating_it(self):
        folder = self.folder / "absent"
        result = load_input(folder)
        self.assertEqual(result.status, "failed")
        self.assertFalse(folder.exists())

    def test_malformed_json_and_nonobjects_keep_line_accountability(self):
        self.write_inputs()
        good = (self.folder / "messages.jsonl").read_bytes()
        (self.folder / "messages.jsonl").write_bytes(b'{bad\n[]\nnull\n"text"\n' + good)
        result = load_input(self.folder)
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.summary()["message_lines_seen"], 5)
        self.assertEqual(result.summary()["messages_indexed"], 1)
        self.assertEqual(result.summary()["rejected_message_lines"], [1, 2, 3, 4])
        self.assertEqual(result.message_records[0].raw_bytes, b"{bad\n")
        self.assertEqual(result.evidence("M1").line, 5)

    def test_invalid_utf8_line_does_not_hide_later_valid_lines(self):
        self.write_inputs()
        good = (self.folder / "messages.jsonl").read_bytes()
        (self.folder / "messages.jsonl").write_bytes(b"\xff\xfe\n" + good)
        result = load_input(self.folder)
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.summary()["rejected_message_lines"], [1])
        self.assertIn("M1", result.messages_by_id)

    def test_nonfinite_constants_and_duplicate_json_keys_rejected(self):
        self.write_inputs(messages=[])
        (self.folder / "messages.jsonl").write_bytes(b'{"id":"A","id":"B"}\n{"ts":NaN}\n')
        result = load_input(self.folder)
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.messages_by_id, {})
        self.assertEqual(self.codes(result), ["malformed_record", "malformed_record"])

    def test_duplicate_message_ids_quarantine_every_occurrence(self):
        for conflicting in (False, True):
            with self.subTest(conflicting=conflicting):
                duplicate = message()
                if conflicting:
                    duplicate["body"] = "Conflicting evidence"
                self.write_inputs(messages=[message(), duplicate, message("unique")])
                result = load_input(self.folder)
                self.assertEqual(result.status, "incomplete")
                self.assertEqual(set(result.messages_by_id), {"unique"})
                self.assertEqual(result.summary()["rejected_message_lines"], [1, 2])
                self.assertEqual(self.codes(result).count("duplicate_id"), 2)
                self.assertEqual(len(result.message_records), 3)
                with self.assertRaises(KeyError):
                    result.evidence("M1")

    def test_duplicate_chat_ids_are_not_overwritten(self):
        self.write_inputs(chats=[chat(), chat()])
        result = load_input(self.folder)
        self.assertEqual(result.chats_by_id, {})
        self.assertEqual(result.messages_by_id, {})
        self.assertIn("unknown_reference", self.codes(result))
        self.assertEqual(result.status, "incomplete")

    def test_duplicate_id_is_quarantined_even_if_one_record_has_bad_metadata(self):
        broken = message()
        broken.pop("body")
        self.write_inputs(messages=[message(), broken])
        result = load_input(self.folder)
        self.assertEqual(result.messages_by_id, {})
        self.assertEqual(self.codes(result).count("duplicate_id"), 2)

    def test_missing_timestamp_preserved_as_undated_evidence(self):
        item = message("undated")
        item.pop("ts")
        self.write_inputs(messages=[item, message("dated", ts=0)])
        result = load_input(self.folder)
        self.assertEqual(result.status, "incomplete")
        self.assertNotIn("ts", result.evidence("undated").original)
        self.assertIsNone(result.evidence("undated").timestamp)
        self.assertEqual([r.original["id"] for r in result.messages_by_chat["C1"]], ["dated", "undated"])
        self.assertEqual(result.summary()["undated_message_ids"], ["undated"])
        self.assertEqual(result.summary()["messages_indexed"], 2)
        self.assertEqual(result.summary()["messages_with_valid_timestamp"], 1)
        self.assertEqual(result.as_of, 0)
        with self.assertRaises(ValueError):
            result.require_complete()

    def test_invalid_timestamp_types_and_ranges_are_not_coerced(self):
        for value in (None, "100", True, [], {}, 10**100, 1e100):
            with self.subTest(value=value):
                item = message(ts=value)
                self.write_inputs(messages=[item])
                result = load_input(self.folder)
                self.assertEqual(result.status, "incomplete")
                self.assertEqual(result.evidence("M1").original["ts"], value)
                self.assertIsNone(result.evidence("M1").timestamp)
                self.assertIsNone(result.as_of)

    def test_fractional_and_negative_unix_seconds_are_valid(self):
        self.write_inputs(messages=[message("fractional", ts=0.5), message("negative", ts=-1)])
        result = load_input(self.folder)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual([r.timestamp for r in result.messages_by_chat["C1"]], [-1, 0.5])

    def test_missing_and_unknown_quotes_do_not_invent_evidence(self):
        missing = message("missing")
        missing.pop("quoted_id")
        unknown = message("unknown")
        unknown["quoted_id"] = "not-in-input"
        self.write_inputs(messages=[missing, unknown])
        result = load_input(self.folder)
        self.assertEqual(result.status, "succeeded")
        self.assertNotIn("quoted_id", result.evidence("missing").original)
        self.assertEqual(result.evidence("unknown").original["quoted_id"], "not-in-input")
        self.assertIn("unresolved_quote", self.codes(result))
        with self.assertRaises(KeyError):
            result.evidence("not-in-input")

    def test_media_placeholders_and_supported_kinds_are_preserved(self):
        records = []
        for index, (kind, body) in enumerate((("image_caption", "[photo]"), ("document", "[document]"),
                                               ("voice_transcript", "Synthetic transcript"))):
            item = message(str(index))
            item.update(kind=kind, body=body)
            records.append(item)
        self.write_inputs(messages=records)
        result = load_input(self.folder)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual([r.original for r in result.message_records], records)

    def test_invalid_metadata_and_unknown_references_are_accounted_for(self):
        no_id = message()
        no_id.pop("id")
        bad_body = message("bad-body")
        bad_body["body"] = None
        self.write_inputs(messages=[no_id, bad_body, message("bad-chat", cid="unknown"),
                                    message("bad-sender", sender="unknown"), message("valid")])
        result = load_input(self.folder)
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.summary()["rejected_message_lines"], [1, 2, 3, 4])
        self.assertEqual(set(result.messages_by_id), {"valid"})

    def test_invalid_chat_metadata_is_reported_without_crashing(self):
        for participants in (None, "P1", [None], [[]]):
            with self.subTest(participants=participants):
                item = chat()
                item["participants"] = participants
                self.write_inputs([item], [])
                result = load_input(self.folder)
                self.assertEqual(result.status, "incomplete")
                self.assertEqual(result.chats_by_id, {})

    def test_invalid_seed_is_not_treated_as_empty_signup(self):
        for raw in (b"", b"{broken", b"[]", b'{"circles": []}', b'{"goals": "bad"}'):
            with self.subTest(raw=raw):
                self.write_inputs([], [])
                (self.folder / "seed.json").write_bytes(raw)
                result = load_input(self.folder)
                self.assertEqual(result.status, "incomplete")
                self.assertIn("invalid_seed", self.codes(result))

    def test_loader_opens_only_three_allowlisted_inputs(self):
        self.write_inputs()
        opened = []
        original_open = Path.open

        def tracked_open(path, *args, **kwargs):
            opened.append(path.name)
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", tracked_open):
            result = load_input(self.folder)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(opened, ["chats.jsonl", "messages.jsonl", "seed.json"])

    def test_answers_named_input_directory_is_rejected_before_open(self):
        with patch.object(Path, "open", side_effect=AssertionError("Must not open any file")):
            result = load_input(self.folder / "answers")
        self.assertEqual(result.status, "failed")

    def test_redirected_input_path_is_rejected_before_open(self):
        self.write_inputs()
        original_resolve = Path.resolve

        def redirected(path, *args, **kwargs):
            if path.name == "messages.jsonl":
                return self.folder / "answers" / "messages.jsonl"
            return original_resolve(path, *args, **kwargs)

        with patch.object(Path, "resolve", redirected):
            result = load_input(self.folder)
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.files_read_complete["messages.jsonl"])

    def test_cli_reports_coverage_and_returns_nonzero_on_incomplete_input(self):
        self.write_inputs(messages=[message(ts=None)])
        completed = subprocess.run([sys.executable, "-B", str(PROJECT / "data.py"), str(self.folder)],
                                   capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 1)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["undated_message_ids"], ["M1"])
        self.assertNotIn("Original text", completed.stdout)


    def test_windows_assign_messages_once_in_chat_order(self):
        self.write_inputs([chat("C2"), chat(), chat("empty")],
                          [message("late", ts=300), message("other", cid="C2"),
                           message("early", ts=100), message("tie", ts=100)])
        data = load_input(self.folder)
        plan = build_windows(data, max_primary_spans=2)
        self.assertEqual([w.chat_id for w in plan.windows], ["C1", "C1", "C2"])
        primary_ids = [s.message_id for w in plan.windows for s in w.primary]
        self.assertEqual(primary_ids, ["early", "tie", "late", "other"])
        self.assertEqual(plan.coverage["fully_covered_messages"], 4)
        self.assertEqual(plan.coverage["primary_span_count"], 4)
        self.assertEqual(plan.coverage["errors"], [])
        plan.require_complete()
        self.assertEqual(plan, build_windows(data, max_primary_spans=2))

    def test_windows_overlap_is_context_only_and_stays_in_chat(self):
        self.write_inputs([chat(), chat("C2")],
                          [message(str(i)) for i in range(4)] + [message("other", cid="C2")])
        data = load_input(self.folder)
        plan = build_windows(data, max_primary_spans=1, overlap_spans=2)
        self.assertEqual([s.message_id for s in plan.windows[2].context], ["0", "1"])
        self.assertEqual(plan.windows[-1].context, ())
        self.assertEqual(plan.coverage["primary_span_count"], 5)
        self.assertEqual(plan.coverage["context_span_count"], 5)
        no_overlap = build_windows(data, max_primary_spans=1, overlap_spans=0)
        self.assertEqual(no_overlap.coverage["primary_span_count"], 5)
        self.assertEqual(no_overlap.coverage["context_span_count"], 0)
        for window in plan.windows:
            self.assertTrue(set(window.primary).isdisjoint(window.context))

    def test_windows_long_unicode_body_has_complete_original_spans(self):
        item = message("  original-id  ", cid="  original-chat  ")
        item["body"] = "Hi नमस्ते বাংলা 👋 kal bhejunga\n" * 3
        item["extra"] = {"keep": True}
        self.write_inputs([chat("  original-chat  ")], [item])
        data = load_input(self.folder)
        record = data.evidence(item["id"])
        original_bytes = record.raw_bytes
        plan = build_windows(data, max_primary_chars=7, overlap_spans=1)
        spans = [s for w in plan.windows for s in w.primary]
        self.assertGreater(len(spans), 1)
        self.assertEqual({s.message_id for s in spans}, {item["id"]})
        self.assertEqual({w.chat_id for w in plan.windows}, {item["chat_id"]})
        self.assertEqual("".join(record.original["body"][s.start:s.end] for s in spans), item["body"])
        self.assertEqual([s.start for s in spans[1:]], [s.end for s in spans[:-1]])
        self.assertEqual((spans[0].start, spans[-1].end), (0, len(item["body"])))
        self.assertEqual(record.original, item)
        self.assertEqual(record.raw_bytes, original_bytes)
        self.assertEqual(plan.coverage["fully_covered_messages"], 1)
        plan.require_complete()

    def test_windows_small_limit_matrix_preserves_every_character(self):
        records = []
        for i, body in enumerate(("", "a", "abcd", "नमस्ते বাংলা", "x" * 17)):
            item = message(str(i))
            item["body"] = body
            records.append(item)
        self.write_inputs(messages=records)
        data = load_input(self.folder)
        for size in (1, 4, 5, 17, 100):
            for count in (1, 3):
                for overlap in (0, 1, 3):
                    with self.subTest(size=size, count=count, overlap=overlap):
                        plan = build_windows(data, size, count, overlap)
                        plan.require_complete()
                        rebuilt = {r["id"]: "" for r in records}
                        for window in plan.windows:
                            self.assertLessEqual(len(window.primary), count)
                            self.assertLessEqual(sum(s.end - s.start for s in window.primary), size)
                            self.assertLessEqual(len(window.context), overlap)
                            for span in window.primary:
                                rebuilt[span.message_id] += data.evidence(span.message_id).original["body"][span.start:span.end]
                        self.assertEqual(rebuilt, {r["id"]: r["body"] for r in records})
                        self.assertEqual(plan.coverage["fully_covered_messages"], len(records))

    def test_windows_empty_body_still_has_one_primary_assignment(self):
        item = message()
        item["body"] = ""
        self.write_inputs(messages=[item])
        plan = build_windows(load_input(self.folder))
        self.assertEqual(plan.windows[0].primary, (MessageSpan("M1", 0, 0),))
        self.assertEqual(plan.coverage["primary_span_count"], 1)
        plan.require_complete()

    def test_windows_empty_inputs_and_zero_message_chat(self):
        for chats in ([], [chat()]):
            with self.subTest(chats=chats):
                self.write_inputs(chats, [])
                plan = build_windows(load_input(self.folder))
                self.assertEqual(plan.windows, ())
                self.assertEqual(plan.coverage["status"], "succeeded_empty")
                self.assertEqual(plan.coverage["primary_span_count"], 0)
                plan.require_complete()

    def test_windows_undated_evidence_retained_but_completion_blocked(self):
        undated = message("undated")
        undated.pop("ts")
        self.write_inputs(messages=[undated, message("invalid", ts="bad"), message("dated", ts=0)])
        data = load_input(self.folder)
        plan = build_windows(data, max_primary_spans=1)
        self.assertEqual([w.primary[0].message_id for w in plan.windows], ["dated", "undated", "invalid"])
        self.assertEqual(plan.coverage["undated_message_ids"], ["undated", "invalid"])
        self.assertEqual(plan.coverage["fully_covered_messages"], 3)
        self.assertEqual(plan.coverage["status"], "incomplete")
        self.assertIsNone(data.evidence("undated").timestamp)
        self.assertNotIn("ts", data.evidence("undated").original)
        self.assertEqual(data.evidence("invalid").original["ts"], "bad")
        with self.assertRaises(ValueError):
            plan.require_complete()

    def test_windows_rejected_records_cannot_be_reported_as_complete(self):
        self.write_inputs(messages=[message("duplicate"), message("duplicate"), message("valid")])
        with (self.folder / "messages.jsonl").open("ab") as stream:
            stream.write(b"{bad\n")
        plan = build_windows(load_input(self.folder))
        self.assertEqual(plan.coverage["status"], "incomplete")
        self.assertEqual(plan.coverage["rejected_message_lines"], [1, 2, 4])
        self.assertEqual(plan.coverage["fully_covered_messages"], 1)
        self.assertEqual(plan.windows[0].primary[0].message_id, "valid")
        with self.assertRaises(ValueError):
            plan.require_complete()

    def test_windows_failed_and_all_rejected_inputs_are_not_successful_empty(self):
        self.write_inputs(messages=[message(), message()])
        data = load_input(self.folder)
        plan = build_windows(data)
        self.assertEqual(plan.windows, ())
        self.assertEqual(plan.coverage["status"], "incomplete")
        (self.folder / "seed.json").unlink()
        failed = build_windows(load_input(self.folder))
        self.assertEqual(failed.coverage["status"], "failed")
        with self.assertRaises(ValueError):
            failed.require_complete()
        self.write_inputs()
        (self.folder / "seed.json").unlink()
        partial = build_windows(load_input(self.folder))
        self.assertEqual(partial.coverage["fully_covered_messages"], 1)
        self.assertEqual(partial.coverage["status"], "failed")

    def test_windows_bad_configuration_is_rejected(self):
        self.write_inputs()
        data = load_input(self.folder)
        for kwargs in ({"max_primary_chars": 0}, {"max_primary_spans": -1},
                       {"overlap_spans": -1}, {"max_primary_chars": True},
                       {"max_primary_spans": 1.5}, {"overlap_spans": "2"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                build_windows(data, **kwargs)

    def test_coverage_validator_rejects_missing_duplicate_and_overlapping_spans(self):
        item = message()
        item["body"] = "abcdef"
        self.write_inputs(messages=[item])
        data = load_input(self.folder)
        invalid = [(), (MessageSpan("M1", 0, 3),),
                   (MessageSpan("M1", 0, 6), MessageSpan("M1", 0, 6)),
                   (MessageSpan("M1", 0, 4), MessageSpan("M1", 3, 6)),
                   (MessageSpan("M1", 0, 2), MessageSpan("M1", 3, 6))]
        for spans in invalid:
            with self.subTest(spans=spans):
                windows = (ProcessingWindow("C1", spans),)
                coverage = validate_window_coverage(data, windows)
                self.assertEqual(coverage["status"], "incomplete")
                self.assertTrue(coverage["errors"])
                with self.assertRaises(ValueError):
                    WindowPlan(windows, coverage).require_complete()
        # The same primary span repeated in separate windows also fails.
        window = build_windows(data).windows[0]
        self.assertEqual(validate_window_coverage(data, (window, window))["status"], "incomplete")

    def test_coverage_validator_context_cannot_cover_missing_primary(self):
        self.write_inputs(messages=[message("first"), message("second")])
        data = load_input(self.folder)
        first = MessageSpan("first", 0, 13)
        second = MessageSpan("second", 0, 13)
        invalid = [
            (ProcessingWindow("C1", (second,), (first,)),),
            (ProcessingWindow("C1", (first,)), ProcessingWindow("C1", (second,), (first, first))),
        ]
        for windows in invalid:
            self.assertEqual(validate_window_coverage(data, windows)["status"], "incomplete")

    def test_coverage_validator_rejects_invalid_evidence_offsets_and_wrong_chat(self):
        self.write_inputs([chat(), chat("C2")])
        data = load_input(self.folder)
        for span in (MessageSpan("unknown", 0, 1), MessageSpan("M1", -1, 13),
                     MessageSpan("M1", 0, 999), MessageSpan("M1", 0, 0),
                     MessageSpan("M1", False, 13)):
            with self.subTest(span=span):
                coverage = validate_window_coverage(data, (ProcessingWindow("C1", (span,)),))
                self.assertEqual(coverage["status"], "incomplete")
        for cid in ("C2", "missing-chat"):
            coverage = validate_window_coverage(data, (ProcessingWindow(cid, (MessageSpan("M1", 0, 13),)),))
            self.assertEqual(coverage["status"], "incomplete")

    def test_context_overlap_rejects_stale_or_skipped_predecessors(self):
        self.write_inputs(messages=[message(str(i)) for i in range(4)])
        data = load_input(self.folder)
        plan = build_windows(data, max_primary_spans=1)
        primary = [w.primary[0] for w in plan.windows]
        for context in ((primary[0],), (primary[0], primary[2])):
            with self.subTest(context=context):
                windows = plan.windows[:-1] + (ProcessingWindow("C1", (primary[3],), context),)
                coverage = validate_window_coverage(data, windows)
                self.assertEqual(coverage["status"], "incomplete")
                self.assertEqual(coverage["fully_covered_messages"], 4)
                self.assertEqual(coverage["primary_span_count"], 4)

    def test_context_overlap_rejects_out_of_order_context(self):
        self.write_inputs(messages=[message(str(i)) for i in range(3)])
        data = load_input(self.folder)
        plan = build_windows(data, max_primary_spans=1)
        last = plan.windows[-1]
        windows = plan.windows[:-1] + (ProcessingWindow("C1", last.primary, tuple(reversed(last.context))),)
        coverage = validate_window_coverage(data, windows)
        self.assertEqual(coverage["status"], "incomplete")
        self.assertEqual(coverage["fully_covered_messages"], 3)

    def test_context_overlap_rejects_excess_context(self):
        self.write_inputs(messages=[message(str(i)) for i in range(4)])
        data = load_input(self.folder)
        plan = build_windows(data, max_primary_spans=1)
        context = tuple(w.primary[0] for w in plan.windows[:-1])
        windows = plan.windows[:-1] + (ProcessingWindow("C1", plan.windows[-1].primary, context),)
        coverage = validate_window_coverage(data, windows)
        self.assertEqual(coverage["status"], "incomplete")
        self.assertEqual(coverage["fully_covered_messages"], 4)

    def test_context_overlap_custom_limits_and_optional_suffix(self):
        self.write_inputs(messages=[message(str(i)) for i in range(4)])
        data = load_input(self.folder)
        for limit in (0, 1, 3):
            with self.subTest(limit=limit):
                plan = build_windows(data, max_primary_spans=1, overlap_spans=limit)
                plan.require_complete()
                self.assertEqual(plan.coverage["overlap_spans"], limit)
                self.assertEqual(validate_window_coverage(data, plan.windows, limit)["status"], "succeeded")
                if limit:
                    self.assertEqual(validate_window_coverage(data, plan.windows, limit - 1)["status"], "incomplete")
        plan = build_windows(data, max_primary_spans=1, overlap_spans=3)
        last = plan.windows[-1]
        for context in ((), last.context[-1:], last.context[-2:]):
            windows = plan.windows[:-1] + (ProcessingWindow("C1", last.primary, context),)
            self.assertEqual(validate_window_coverage(data, windows, 3)["status"], "succeeded")
        for limit in (-1, True, 1.5, "2"):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                validate_window_coverage(data, plan.windows, limit)

    def test_context_overlap_history_is_per_chat(self):
        self.write_inputs([chat(), chat("C2")], [message("a"), message("b", cid="C2"), message("c")])
        data = load_input(self.folder)
        a, b, c = (MessageSpan(mid, 0, 13) for mid in ("a", "b", "c"))
        windows = (ProcessingWindow("C1", (a,)), ProcessingWindow("C2", (b,)),
                   ProcessingWindow("C1", (c,), (a,)))
        self.assertEqual(validate_window_coverage(data, windows, 1)["status"], "succeeded")
        wrong_chat = windows[:-1] + (ProcessingWindow("C1", (c,), (b,)),)
        coverage = validate_window_coverage(data, wrong_chat, 1)
        self.assertEqual(coverage["status"], "incomplete")
        self.assertEqual(coverage["fully_covered_messages"], 3)
        self.assertEqual(coverage["primary_span_count"], 3)

    def test_coverage_validator_rejects_out_of_order_primary_spans(self):
        self.write_inputs(messages=[message("early", ts=1), message("late", ts=2)])
        data = load_input(self.folder)
        plan = build_windows(data, max_primary_spans=1, overlap_spans=0)
        coverage = validate_window_coverage(data, tuple(reversed(plan.windows)))
        self.assertEqual(coverage["status"], "incomplete")
        self.assertTrue(any("chronology" in error for error in coverage["errors"]))


if __name__ == "__main__":
    unittest.main()
