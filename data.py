"""Stage A: read only the three permitted inputs and retain their evidence.

No predictions, model calls, answer loading, or output-schema processing live here.
Run ``python data.py <input_dir>`` for a metadata-only loading report.
"""

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


Timestamp = Union[int, float]
INPUT_FILES = ("chats.jsonl", "messages.jsonl", "seed.json")
MESSAGE_KINDS = {"text", "voice_transcript", "image_caption", "document"}


@dataclass
class Issue:
    file: str
    line: Optional[int]
    code: str
    detail: str
    severity: str = "error"


@dataclass
class InputRecord:
    """One nonblank source line, including rejected lines for accountability."""

    file: str
    line: int
    raw_bytes: bytes
    original: Any = None
    indexed: bool = False
    timestamp: Optional[Timestamp] = None


@dataclass
class InputData:
    chat_records: List[InputRecord] = field(default_factory=list)
    message_records: List[InputRecord] = field(default_factory=list)
    seed: Optional[dict] = None
    seed_raw_bytes: Optional[bytes] = None
    chats_by_id: Dict[str, InputRecord] = field(default_factory=dict)
    messages_by_id: Dict[str, InputRecord] = field(default_factory=dict)
    messages_by_chat: Dict[str, List[InputRecord]] = field(default_factory=dict)
    messages_by_sender: Dict[str, List[InputRecord]] = field(default_factory=dict)
    person_ids: Tuple[str, ...] = ()
    files_read_complete: Dict[str, bool] = field(default_factory=dict)
    issues: List[Issue] = field(default_factory=list)

    @property
    def status(self):
        if not all(self.files_read_complete.get(name, False) for name in INPUT_FILES):
            return "failed"
        if any(issue.severity == "error" for issue in self.issues):
            return "incomplete"
        if not self.chats_by_id and not self.messages_by_id:
            return "succeeded_empty"
        return "succeeded"

    @property
    def as_of(self):
        """Latest known timestamp; it is not a complete endpoint on an invalid load."""
        times = [r.timestamp for r in self.messages_by_id.values() if r.timestamp is not None]
        return max(times) if times else None

    def require_complete(self):
        """Future callers must use this gate before treating input as complete."""
        if self.status not in {"succeeded", "succeeded_empty"}:
            raise ValueError("Input loading is %s; inspect issues before proceeding." % self.status)

    def evidence(self, message_id):
        """Return a uniquely indexed source record; unknown/ambiguous IDs raise KeyError."""
        return self.messages_by_id[message_id]

    def summary(self):
        """Report coverage without exposing chat names, bodies, or signup facts."""
        undated = [mid for mid, r in self.messages_by_id.items() if r.timestamp is None]
        return {
            "status": self.status,
            "files_read_complete": dict(self.files_read_complete),
            "chats_indexed": len(self.chats_by_id),
            "people": len(self.person_ids),
            "message_lines_seen": len(self.message_records),
            "message_objects_parsed": sum(isinstance(r.original, dict) for r in self.message_records),
            "messages_indexed": len(self.messages_by_id),
            "messages_with_valid_timestamp": len(self.messages_by_id) - len(undated),
            "undated_message_ids": undated,
            "rejected_message_lines": [r.line for r in self.message_records if not r.indexed],
            "as_of": self.as_of,
            "issues": [vars(issue).copy() for issue in self.issues],
        }


def _permitted_path(folder, name):
    """Resolve an allowlisted filename without scanning the input directory."""
    if name not in INPUT_FILES:
        raise ValueError("Not a permitted input filename.")
    root = Path(folder).resolve()
    if any(part.casefold() == "answers" for part in root.parts):
        raise ValueError("An answers directory cannot be used as input.")
    path = (root / name).resolve()
    if path.parent != root or path.name != name:
        raise ValueError("Input file redirects outside its permitted path.")
    return path


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key.")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Non-finite JSON number: " + value)


def _parse(raw):
    # utf-8-sig accepts an optional BOM without changing the retained source bytes.
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object,
                      parse_constant=_reject_constant)


def _read_jsonl(folder, name, result):
    records = []
    result.files_read_complete[name] = False
    try:
        with _permitted_path(folder, name).open("rb") as stream:
            for line, raw in enumerate(stream, 1):
                if not raw.strip():
                    continue
                record = InputRecord(name, line, raw)
                records.append(record)
                try:
                    record.original = _parse(raw)
                    if not isinstance(record.original, dict):
                        raise ValueError("Each JSONL record must be an object.")
                except (ValueError, UnicodeError, RecursionError):
                    result.issues.append(Issue(name, line, "malformed_record",
                                               "Invalid UTF-8, JSON, or non-object record."))
        result.files_read_complete[name] = True
    except (OSError, ValueError, RuntimeError):
        result.issues.append(Issue(name, None, "unreadable_file",
                                   "Required input is missing, unreadable, or redirects outside the allowed path."))
    return records


def _unique_records(records, key, issues):
    """Quarantine every occurrence of a duplicate ID, including identical copies."""
    groups = defaultdict(list)
    for record in records:
        if not isinstance(record.original, dict):
            continue  # The parser already reported this line.
        identifier = record.original.get(key)
        if not isinstance(identifier, str) or not identifier.strip():
            issues.append(Issue(record.file, record.line, "invalid_id",
                                "Missing or non-string " + key + "."))
        else:
            groups[identifier].append(record)
    unique = []
    for group in groups.values():
        if len(group) > 1:
            for record in group:
                issues.append(Issue(record.file, record.line, "duplicate_id",
                                    "Ambiguous %s; first occurrence is line %d." % (key, group[0].line)))
        else:
            unique.append(group[0])
    return unique


def _valid_timestamp(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        if not math.isfinite(value):
            return False
        datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=value)
        return True
    except (OverflowError, ValueError):
        return False


def _order(record):
    # Unknown dates form a separate trailing partition, not an invented chronology.
    return (record.timestamp is None,
            record.timestamp if record.timestamp is not None else 0,
            record.line)


def _load_seed(folder, result):
    name = "seed.json"
    result.files_read_complete[name] = False
    try:
        result.seed_raw_bytes = _permitted_path(folder, name).read_bytes()
        result.files_read_complete[name] = True
        value = _parse(result.seed_raw_bytes)
        if not isinstance(value, dict):
            raise ValueError("Seed must be an object.")
        result.seed = value
        circles = value.get("circles", {})
        organisations = value.get("organisations", [])
        goals = value.get("goals", [])
        if not (isinstance(circles, dict)
                and all(isinstance(k, str) and k.strip() and isinstance(v, str) for k, v in circles.items())
                and isinstance(organisations, list) and all(isinstance(o, str) for o in organisations)
                and isinstance(goals, list) and all(isinstance(g, dict) for g in goals)):
            raise ValueError("Invalid seed field structure.")
    except (OSError, ValueError, UnicodeError, RuntimeError, RecursionError):
        result.issues.append(Issue(name, None, "invalid_seed",
                                   "Required seed is missing, unreadable, or has invalid JSON/field structure."))


def load_input(input_dir):
    """Load inputs and return an auditable partial result if any record fails.

    Inspect status/issues or call require_complete() before later processing.
    Indexed records retain their original dictionaries and exact source-line bytes.
    Do not mutate those dictionaries in downstream stages.
    """
    result = InputData()
    result.chat_records = _read_jsonl(input_dir, "chats.jsonl", result)
    result.message_records = _read_jsonl(input_dir, "messages.jsonl", result)
    _load_seed(input_dir, result)

    for record in _unique_records(result.chat_records, "chat_id", result.issues):
        chat = record.original
        participants = chat.get("participants")
        if not (isinstance(chat.get("name"), str) and isinstance(chat.get("is_group"), bool)
                and isinstance(participants, list)
                and all(isinstance(p, str) and p.strip() for p in participants)):
            result.issues.append(Issue(record.file, record.line, "invalid_chat", "Invalid chat metadata."))
            continue
        record.indexed = True
        result.chats_by_id[chat["chat_id"]] = record
        result.messages_by_chat[chat["chat_id"]] = []

    people = {p for r in result.chats_by_id.values() for p in r.original["participants"]}
    result.person_ids = tuple(sorted(people - {"ME"}))
    known_senders = people | {"ME"}
    result.messages_by_sender = {pid: [] for pid in sorted(known_senders)}
    for record in _unique_records(result.message_records, "id", result.issues):
        message = record.original
        cid, sender = message.get("chat_id"), message.get("sender_id")
        quoted = message.get("quoted_id")
        if not (isinstance(cid, str) and isinstance(sender, str)
                and isinstance(message.get("body"), str)
                and isinstance(message.get("sender_name"), str)
                and isinstance(message.get("kind"), str) and message["kind"] in MESSAGE_KINDS
                and (quoted is None or isinstance(quoted, str) and quoted.strip())):
            result.issues.append(Issue(record.file, record.line, "invalid_message", "Invalid message metadata."))
            continue
        if cid not in result.chats_by_id or sender not in known_senders:
            result.issues.append(Issue(record.file, record.line, "unknown_reference",
                                       "Chat or sender is absent from valid chat metadata."))
            continue
        if sender not in result.chats_by_id[cid].original["participants"]:
            result.issues.append(Issue(record.file, record.line, "sender_not_in_chat",
                                       "Known sender is not listed in this chat's participants.", "warning"))
        if _valid_timestamp(message.get("ts")):
            record.timestamp = message["ts"]
        else:
            result.issues.append(Issue(record.file, record.line, "invalid_timestamp",
                                       "Missing/invalid Unix seconds; retained as undated evidence."))
        record.indexed = True
        result.messages_by_id[message["id"]] = record
        result.messages_by_chat[cid].append(record)
        result.messages_by_sender[sender].append(record)

    for records in result.messages_by_chat.values():
        records.sort(key=_order)
    for records in result.messages_by_sender.values():
        records.sort(key=_order)
    for record in result.messages_by_id.values():
        quoted = record.original.get("quoted_id")
        if quoted is not None and quoted not in result.messages_by_id:
            result.issues.append(Issue(record.file, record.line, "unresolved_quote",
                                       "Quoted message is unavailable or ambiguous; no evidence invented.", "warning"))
    return result


@dataclass(frozen=True)
class MessageSpan:
    """Half-open Python character offsets into an unchanged original message body."""

    message_id: str
    start: int
    end: int


@dataclass(frozen=True)
class ProcessingWindow:
    chat_id: str
    primary: Tuple[MessageSpan, ...]
    context: Tuple[MessageSpan, ...] = ()


@dataclass(frozen=True)
class WindowPlan:
    windows: Tuple[ProcessingWindow, ...]
    coverage: dict

    def require_complete(self):
        """Assignment success is not evidence that extraction has run."""
        if self.coverage["status"] not in {"succeeded", "succeeded_empty"}:
            raise ValueError("Window assignment is " + self.coverage["status"])


def build_windows(data, max_primary_chars=4000, max_primary_spans=32, overlap_spans=2):
    """Assign indexed messages/spans once, retaining partial-input diagnostics.

    Limits count Python characters/spans, not model tokens. Context adds at most
    overlap_spans * max_primary_chars body characters. Metadata is not budgeted.
    A normal message stays whole; only bodies exceeding max_primary_chars split.
    """
    for name, value, minimum in (("max_primary_chars", max_primary_chars, 1),
                                 ("max_primary_spans", max_primary_spans, 1),
                                 ("overlap_spans", overlap_spans, 0)):
        if type(value) is not int or value < minimum:
            raise ValueError(name + " must be an integer >= " + str(minimum))

    windows = []
    for chat_id in sorted(data.messages_by_chat):
        spans = []
        for record in data.messages_by_chat[chat_id]:
            body = record.original["body"]
            # An empty body still has one assignable evidence unit: [0, 0).
            for start in range(0, max(1, len(body)), max_primary_chars):
                spans.append(MessageSpan(record.original["id"], start,
                                         min(start + max_primary_chars, len(body))))
        cursor = 0
        while cursor < len(spans):
            first = cursor
            size = 0
            while cursor < len(spans) and cursor - first < max_primary_spans:
                length = spans[cursor].end - spans[cursor].start
                if size + length > max_primary_chars:
                    break
                size += length
                cursor += 1
            windows.append(ProcessingWindow(
                chat_id, tuple(spans[first:cursor]),
                tuple(spans[max(0, first - overlap_spans):first])))
    windows = tuple(windows)
    return WindowPlan(windows, validate_window_coverage(data, windows, overlap_spans))


def validate_window_coverage(data, windows, overlap_spans=2):
    """Check coverage against original bodies, independently of the splitter.

    Coverage requires contiguous non-overlapping primary intervals for every
    indexed message. Nonempty context must be an ordered, contiguous suffix of
    preceding primary spans in the same chat, with at most overlap_spans entries.
    The suffix may cross earlier window boundaries; context is optional.
    Revalidation must use the same overlap limit as construction.
    Rejected source records remain explicit; partial input can never pass the gate.
    This validates internal typed window records, not arbitrary model JSON.
    """
    if type(overlap_spans) is not int or overlap_spans < 0:
        raise ValueError("overlap_spans must be an integer >= 0")
    errors = []
    intervals = defaultdict(list)
    previous = set()
    recent_by_chat = defaultdict(list)
    last_order = {}
    primary_count = context_count = 0
    for window_index, window in enumerate(windows):
        if window.chat_id not in data.chats_by_id:
            errors.append("Unknown chat in window %d." % window_index)
        if not window.primary:
            errors.append("Window %d has no primary spans." % window_index)
        recent = recent_by_chat[window.chat_id]
        if len(window.context) > overlap_spans:
            errors.append("Context exceeds configured overlap limit in window %d." % window_index)
        elif window.context and tuple(window.context) != tuple(recent[-len(window.context):]):
            errors.append("Context is not the ordered immediately preceding suffix in window %d."
                          % window_index)
        current = set()
        for role, spans in (("context", window.context), ("primary", window.primary)):
            for span in spans:
                if role == "primary":
                    primary_count += 1
                else:
                    context_count += 1
                record = data.messages_by_id.get(span.message_id)
                if record is None or record.original["chat_id"] != window.chat_id:
                    errors.append("Unknown or wrong-chat evidence in window %d." % window_index)
                    continue
                length = len(record.original["body"])
                if not (type(span.start) is int and type(span.end) is int
                        and 0 <= span.start <= span.end <= length
                        and (span.start < span.end or length == 0)):
                    errors.append("Invalid span offsets in window %d." % window_index)
                    continue
                if role == "context":
                    continue
                if span in previous or span in current:
                    errors.append("Duplicate primary span in window %d." % window_index)
                current.add(span)
                intervals[span.message_id].append((span.start, span.end))
                order = _order(record) + (span.start,)
                if window.chat_id in last_order and order < last_order[window.chat_id]:
                    errors.append("Primary spans out of source chronology in window %d." % window_index)
                last_order[window.chat_id] = order
        previous.update(current)
        recent_by_chat[window.chat_id] = (
            (recent + list(window.primary))[-overlap_spans:] if overlap_spans else [])

    fully_covered = 0
    for mid, record in data.messages_by_id.items():
        parts = sorted(intervals[mid])
        length = len(record.original["body"])
        cursor = 0
        complete = bool(parts)
        for start, end in parts:
            if start != cursor:
                complete = False
            cursor = end
        complete = complete and cursor == length
        if length == 0:
            complete = parts == [(0, 0)]
        if complete:
            fully_covered += 1
        else:
            errors.append("Missing, overlapping, or repeated primary coverage for message " + mid)

    if data.status == "failed":
        status = "failed"
    elif data.status == "incomplete" or errors:
        status = "incomplete"
    else:
        status = "succeeded" if data.messages_by_id else "succeeded_empty"
    return {
        "status": status,
        "input_status": data.status,
        "indexed_messages": len(data.messages_by_id),
        "fully_covered_messages": fully_covered,
        "primary_span_count": primary_count,
        "context_span_count": context_count,
        "overlap_spans": overlap_spans,
        "undated_message_ids": [mid for mid, r in data.messages_by_id.items() if r.timestamp is None],
        "rejected_message_lines": [r.line for r in data.message_records if not r.indexed],
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", help="Directory containing only the permitted inputs to load.")
    args = parser.parse_args()
    result = load_input(args.input_dir)
    print(json.dumps(result.summary(), ensure_ascii=True, indent=2))
    return 0 if result.status in {"succeeded", "succeeded_empty"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
