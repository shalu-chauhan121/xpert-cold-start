#!/usr/bin/env python3
"""Production pipeline: python3 solution.py <input_dir> <output.json>.
Use run.sh on Linux for the outer process-group deadline supervisor.
"""
import json
import os
import sys
import uuid
import time
from pathlib import Path

from data import load_input, build_windows
from llm import Client, Budget, Deadline, LLMError
from validation import SchemaValidator, read_json, validate_output


def assemble_output(data, client=None, deadline=None, summary=None):
    """Run existing stages, gate prerequisites, and retain diagnostics separately."""
    from reasoning import (extract_windows, resolve_organisations, resolve_entities,
                           resolve_goals, review_task_packet, resolve_help)
    from tasks import build_ledger
    data.require_complete()
    deadline = deadline or Deadline()
    summary = summary if summary is not None else {}
    summary.update(state="running", stages={})
    output = {key: [] for key in ("people", "organisations", "chats", "goals", "open_loops")}
    if not data.chats_by_id and not data.messages_by_id and not any(data.seed.values()):
        summary["state"] = "succeeded_empty"
        return output
    if not data.messages_by_id and any(data.seed.get(k) for k in ("goals", "organisations")):
        raise ValueError("Incomplete: seed-only intentions/entities require message evidence and review.")
    if client is None:
        try:
            ceiling = os.environ.get("LLM_TOKEN_CEILING")
            planned = os.environ.get("LLM_PLANNED_BASE_CALLS")
            budget = Budget(None if ceiling is None else int(ceiling),
                            None if planned is None else int(planned))
        except ValueError:
            raise ValueError("Invalid run budget configuration") from None
        client = Client(budget=budget, deadline=deadline)
        client._configuration(None)  # Fail before stage work on missing credentials.
    else:
        client.deadline = deadline
    def accept(name, result):
        summary["stages"][name] = result
        summary["usage"] = client.budget.summary()
        if result["state"] not in ("succeeded", "succeeded_empty"):
            summary["state"] = "incomplete"
            raise ValueError("Incomplete stage: " + name)
        deadline.check(finalizing=True)
        return result
    plan = build_windows(data)
    plan.require_complete()
    extraction = accept("extraction", extract_windows(data, plan, client, timezone_policy="UTC"))
    organisations = accept("organisations", resolve_organisations(data, extraction, client))
    entities = accept("entities", resolve_entities(data, extraction, organisations, client))
    goals = accept("goals", resolve_goals(data, extraction, client))
    ledger = accept("tasks", build_ledger(data, extraction,
                    lambda packet, validate: review_task_packet(client, packet, validate)))
    output.update(people=entities["people"], organisations=organisations["items"],
                  chats=entities["chats"], goals=goals["items"])
    for task in ledger["tasks"]:
        item = {"title": task["action"] + " " + task["object"], "type": task["type"],
                "owner": task["owner"], "chat_id": task["chat_id"],
                "source_msg": task["source_msg"], "status": task["status"], "due": task["due"]}
        if task["closed_by"] is not None:
            item["closed_by"] = task["closed_by"]
        output["open_loops"].append(item)
    output = accept("help", resolve_help(data, output, ledger, client))["output"]
    deadline.check(finalizing=True)
    validate_output(output, data)
    summary["state"] = "succeeded"
    summary["usage"] = client.budget.summary()
    return output


def export_output(output, data, output_path, deadline=None):
    """Validate, write beside destination, close/revalidate, atomically replace.

    Exclusive creation avoids clobbering another writer's temporary file. No
    final path is opened for writing. Ordinary failures and KeyboardInterrupt
    clean up owned temporaries; an uncatchable kill can leave an unpublished temp.
    """
    if deadline is not None:
        deadline.check(finalizing=True)
    validator = SchemaValidator()
    validate_output(output, data, validator)
    destination = Path(output_path).absolute()
    temporary = destination.with_name("." + destination.name + "." + uuid.uuid4().hex + ".tmp")
    owned = False
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            owned = True
            json.dump(output, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        with temporary.open(encoding="utf-8") as stream:
            serialized = read_json(stream)
        validate_output(serialized, data, validator)
        if serialized != output:
            raise ValueError("Serialized output differs from the validated in-memory output")
        if deadline is not None:
            deadline.check(finalizing=True)
        os.replace(temporary, destination)
    finally:
        if owned:
            temporary.unlink(missing_ok=True)


def main(input_dir, output_path, *, client=None, deadline=None, summary=None):
    deadline = deadline or Deadline(started=time.monotonic())
    summary = summary if summary is not None else {}
    try:
        deadline.check(finalizing=True)
        data = load_input(input_dir)
        data.require_complete()
        output = assemble_output(data, client=client, deadline=deadline, summary=summary)
        export_output(output, data, output_path, deadline=deadline)
    except (OSError, ValueError, UnicodeError, RecursionError, LLMError) as error:
        summary["state"] = "incomplete"
        print("Run failed: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
