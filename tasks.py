"""Stage F: evidence-backed task ledger. No help or final orchestration.

build_ledger takes an injected reviewer(packet, validate), normally a bound
reasoning.review_task_packet. No client or network connection is created here.
"""
import copy
import hashlib
import json
import re
from datetime import date


class TaskError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise TaskError(message)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def identifier(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def evidence_ids(observation, data):
    require(isinstance(observation.get("evidence"), list) and observation["evidence"], "Missing evidence")
    ids = set()
    for span in observation["evidence"]:
        require(isinstance(span, dict) and set(span) == {"message_id", "start", "end", "text"}, "Invalid evidence")
        mid, start, end = span["message_id"], span["start"], span["end"]
        require(isinstance(mid, str) and mid in data.messages_by_id, "Unknown source")
        body = data.messages_by_id[mid].original["body"]
        require(type(start) is int and type(end) is int and 0 <= start < end <= len(body)
                and span["text"] == body[start:end], "Invalid supporting span")
        ids.add(mid)
    return ids


def validate_event(event, observation, data):
    require(isinstance(event, dict) and set(event) == {"operation", "source_msg", "evidence", "details"}, "Invalid event fields")
    operation = event["operation"]
    require(operation in ("create", "acknowledge", "update", "complete", "cancel", "reopen", "ambiguous"), "Invalid operation")
    supplied = evidence_ids(observation, data)
    require(isinstance(event["evidence"], list) and event["evidence"] and
            all(isinstance(i, str) and i in supplied for i in event["evidence"]), "Unsupported event citations")
    require(event["source_msg"] in event["evidence"], "Missing event source")
    require(data.messages_by_id[event["source_msg"]].timestamp is not None, "Undated event")
    details = event["details"]
    require(isinstance(details, dict), "Invalid details")
    if operation == "create":
        require(observation["kind"] == "task_create", "Update cannot invent a task origin")
        require(set(details) == {"action", "object", "type", "owner", "due"}, "Incomplete creation")
        require(all(isinstance(details[k], str) and details[k].strip() for k in ("action", "object")), "Missing task meaning")
        require(details["type"] in ("commitment", "followup", "deadline", "question"), "Invalid task type")
    elif operation == "update":
        require(details and set(details) <= {"owner", "due"}, "Unsupported update fields")
    else:
        require(not details, "Unexpected operation details")
    if "owner" in details:
        require(details["owner"] in set(data.person_ids) | {"ME"}, "Unknown owner")
    if details.get("due") is not None:
        due = details["due"]
        require(isinstance(due, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", due), "Invalid due date")
        date.fromisoformat(due)


def candidates(event, ledger, data):
    """Ordered retrieval only. A reply/word match never authorizes a merge."""
    source = data.messages_by_id[event["source_msg"]].original
    chat = source["chat_id"]
    participants = set(data.chats_by_id[chat].original["participants"]) - {"ME"}
    words = set(re.findall(r"\w+", source["body"].casefold()))
    ranked = []
    for task in ledger.values():
        if source.get("quoted_id") in task["evidence"]:
            priority = 0
        elif task["chat_id"] == chat:
            priority = 1
        else:
            others = set(data.chats_by_id[task["chat_id"]].original["participants"]) - {"ME"}
            specifics = set(re.findall(r"\w+", task["object"].casefold()))
            if not (participants & others and words & specifics):
                continue
            priority = 2
        ranked.append((priority, task["id"]))
    return [ledger[tid] for _, tid in sorted(ranked)]


def replay(task, data):
    """Replay accepted events; simultaneous conflicting mutations remain pending."""
    events = sorted(task["events"], key=lambda e: (data.messages_by_id[e["source_msg"]].timestamp,
                                                   data.messages_by_id[e["source_msg"]].line, e["id"]))
    result = copy.deepcopy(task)
    origin = next(e for e in events if e["operation"] == "create" and
                  "task_" + e["id"][:24] == task["id"])
    result.update(origin["details"])
    result["owner_evidence"] = origin["evidence"]
    result["due_evidence"] = origin["evidence"] if origin["details"]["due"] else []
    result.update(status="open", closed_by=None, conflicts=[], events=events)
    origin_time = data.messages_by_id[task["source_msg"]].timestamp
    buckets = {}
    applied_ids = set()
    for event in events:
        if event["id"] in applied_ids:
            continue  # Keep every provenance record, apply identical semantics once.
        applied_ids.add(event["id"])
        buckets.setdefault(data.messages_by_id[event["source_msg"]].timestamp, []).append(event)
    for timestamp, same_time in sorted(buckets.items()):
        mutations = [e for e in same_time if e["operation"] in ("complete", "cancel", "reopen", "update")]
        changes = {(e["operation"], encoded(e["details"])) for e in mutations}
        if (timestamp < origin_time or len(changes) > 1 or
                timestamp == origin_time and any(e["source_msg"] != task["source_msg"] for e in mutations)):
            result["conflicts"].extend(e["id"] for e in same_time)
            continue
        closures = [e for e in mutations if e["operation"] in ("complete", "cancel")]
        for event in same_time:
            operation = event["operation"]
            if operation == "create" and event["details"] != origin["details"]:
                result["conflicts"].append(event["id"])
            elif operation in ("complete", "cancel"):
                wanted = "done" if operation == "complete" else "dropped"
                if result["status"] not in ("open", wanted):
                    result["conflicts"].append(event["id"])
                    continue
                # Equal-time closures agree on status, but distinct events do
                # not establish a unique closure source. Keep all provenance
                # and let the existing conflict gate mark the ledger incomplete.
                if len(closures) > 1:
                    result["conflicts"].append(event["id"])
                result.update(status=wanted, closed_by=None if len(closures) > 1 else event["source_msg"])
            elif operation == "reopen":
                if result["status"] == "open":
                    result["conflicts"].append(event["id"])
                else:
                    result.update(status="open", closed_by=None)
            elif operation == "update":
                result.update(event["details"])
                if "owner" in event["details"]:
                    result["owner_evidence"] = event["evidence"]
                if "due" in event["details"]:
                    result["due_evidence"] = event["evidence"]
    return result


def build_ledger(data, extraction, reviewer, *, candidate_batch_size=16, max_packet_bytes=60000):
    """Retain every candidate-search disposition; failed partitions stay pending.

    Reviewer returns accepted semantics; this function checks provenance and
    transitions but cannot prove that natural-language evidence entails them.
    """
    data.require_complete()
    require(type(candidate_batch_size) is int and candidate_batch_size > 0, "Invalid candidate batch size")
    require(type(max_packet_bytes) is int and max_packet_bytes > 0, "Invalid packet bound")
    result = {"state": "incomplete", "tasks": [], "required": [], "completed": [],
              "pending": [], "unresolved": [], "failures": [], "searches": []}
    complete = (extraction["state"] in ("succeeded", "succeeded_empty") and
                extraction["required"] == extraction["completed"] and not extraction["failures"])
    observations = {}
    for raw in extraction["observations"]:
        if raw["kind"] not in ("task_create", "task_update"):
            continue
        observation = copy.deepcopy(raw)
        identity = {k: observation[k] for k in ("kind", "subjects", "meaning", "evidence")}
        identity["subjects"] = sorted(set(identity["subjects"]))
        identity["evidence"] = sorted(identity["evidence"], key=encoded)
        oid = identifier(identity)
        if oid not in observations:
            observations[oid] = dict(identity, id=oid, windows=[], extraction_ids=[])
        observations[oid]["windows"] = sorted(set(observations[oid]["windows"] + raw.get("windows", [])))
        observations[oid]["extraction_ids"] = sorted(set(observations[oid]["extraction_ids"] + [raw["id"]]))
    result["required"] = sorted(observations)
    events = []
    def review(packet, validate):
        require(len(encoded(packet)) <= max_packet_bytes, "Task packet too large")
        reply = reviewer(copy.deepcopy(packet), validate)
        validate(reply)
        return reply
    for oid, observation in sorted(observations.items()):
        try:
            supplied = evidence_ids(observation, data)
            packet = {"phase": "interpret", "observation": observation,
                      "messages": {i: data.messages_by_id[i].original for i in sorted(supplied)},
                      "people": list(data.person_ids), "as_of": data.as_of,
                      "contract": 'Return {operation:create|acknowledge|update|complete|cancel|reopen|ambiguous, source_msg, evidence:[IDs], details:{}}. create details require action,object,type,owner,due (null if unknown); type is exactly one of [commitment, followup, deadline, question] - never substitute or invent another value; update details contain only supported owner/due changes. Other details are empty.'}
            event = review(packet, lambda e: validate_event(e, observation, data))
            events.append(dict(event, id=identifier(event), observation_id=oid,
                               provenance=observation))
        except Exception:
            result["pending"].append(oid)
            result["failures"].append({"observation": oid, "code": "interpretation_failed"})
    ledger = {}
    # Origins are installed before matching updates, allowing late discoveries
    # and explicit detection of an update predating its proposed origin.
    events.sort(key=lambda e: (e["operation"] != "create", data.messages_by_id[e["source_msg"]].timestamp,
                              data.messages_by_id[e["source_msg"]].line, e["id"]))
    for event in events:
        oid = event["observation_id"]
        if event["operation"] == "ambiguous":
            result["unresolved"].append({"event": event, "reason": "ambiguous_evidence"})
            result["completed"].append(oid)
            continue
        options = candidates(event, ledger, data)
        matches, failed, ambiguous = [], False, False
        for start in range(0, len(options), candidate_batch_size):
            batch = options[start:start + candidate_batch_size]
            ids = {t["id"] for t in batch}
            source_ids = set(event["evidence"]) | {i for t in batch for i in t["evidence"]}
            search = {"observation": oid, "candidates": sorted(ids), "state": "pending"}
            result["searches"].append(search)
            def validate(reply):
                require(isinstance(reply, dict) and set(reply) == {"decision", "target", "evidence"}, "Invalid match result")
                require(reply["decision"] in ("match", "none", "ambiguous"), "Invalid match decision")
                require(isinstance(reply["evidence"], list) and reply["evidence"] and
                        all(isinstance(i, str) and i in source_ids for i in reply["evidence"]) and
                        event["source_msg"] in reply["evidence"], "Invalid match evidence")
                if reply["decision"] == "match":
                    require(reply["target"] in ids, "Unknown task target")
                    target = next(t for t in batch if t["id"] == reply["target"])
                    require(target["source_msg"] in reply["evidence"], "Match must cite origin")
                else:
                    require(reply["target"] is None, "Unexpected match target")
            try:
                reply = review({"phase": "match", "event": event, "candidates": batch,
                                "messages": {i: data.messages_by_id[i].original for i in sorted(source_ids)},
                                "contract": 'Return {decision:match|none|ambiguous,target:task ID or null,evidence:[message IDs]}. A match requires explicit support for SAME obligation scope, citing event and task origin. Shared participants or similar words alone are not a match.'}, validate)
                search["state"] = "completed"
                search["decision"] = reply
                if reply["decision"] == "match":
                    matches.append(reply["target"])
                ambiguous = ambiguous or reply["decision"] == "ambiguous"
            except Exception:
                failed = True
                result["failures"].append({"observation": oid, "code": "matching_failed"})
        if failed:
            result["pending"].append(oid)
            continue
        if ambiguous or len(matches) > 1:
            result["unresolved"].append({"event": event, "reason": "ambiguous_evidence"})
        elif matches:
            task = ledger[matches[0]]
            task["events"].append(event)
            task["evidence"] = sorted(set(task["evidence"]) | set(event["evidence"]))
        elif event["operation"] == "create":
            tid = "task_" + event["id"][:24]
            if tid in ledger:
                ledger[tid]["events"].append(event)
            else:
                ledger[tid] = dict(event["details"], id=tid, source_msg=event["source_msg"],
                              chat_id=data.messages_by_id[event["source_msg"]].original["chat_id"],
                              owner_evidence=event["evidence"], due_evidence=event["evidence"] if event["details"]["due"] else [],
                              events=[event], evidence=sorted(set(event["evidence"])))
        else:
            result["unresolved"].append({"event": event, "reason": "unmatched_after_review"})
        result["completed"].append(oid)
    result["tasks"] = [replay(ledger[tid], data) for tid in sorted(ledger)]
    conflicts = any(t["conflicts"] for t in result["tasks"])
    result["completed"].sort()
    result["pending"] = sorted(set(result["pending"]))
    if complete and not result["pending"] and not conflicts:
        result["state"] = "succeeded" if result["tasks"] or result["unresolved"] else "succeeded_empty"
    return result
