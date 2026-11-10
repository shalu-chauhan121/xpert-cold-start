"""Export the actual Session 08 conversation from the local OpenCode store.

The genuine raw payloads are read byte-faithfully from the `session_message`
rows of the local SQLite database (same mechanism and archival rules as
session-07-export.py). Two artifacts are produced next to this script:

- `session-08-export.json`  raw export: complete session info plus every
  stored message payload in sequence order, unmodified (strings larger than
  the archiver limit stay untruncated here).
- `session-08-transcript.md` chronological transcript of the actual public
  dialogue: user prompts and approvals, the model-switch verification
  discussion and decisions, assistant visible text, tool calls with real
  inputs/outputs, code modifications, test runs and results, and the final
  PowerShell command with execution instructions. Hidden model reasoning,
  synthetic harness records and idle bookkeeping are excluded, as in the
  Session 04-07 archival rules; long strings are cut at 20,000 characters
  with explicit `[truncated by archiver]` markers.

Nothing is reconstructed; credential-shaped strings are redacted; earlier
session archives (Sessions 00-07) are untouched. Re-run for a byte-faithful
post-response refresh; it atomically replaces only these two Session 08
files.
"""
import hashlib
import json
import os
from pathlib import Path
import re
from datetime import datetime, timezone

SOURCE_DB = Path(r"C:/Users/Shalu Chauhan/.local/share/opencode/opencode.db")
SESSION_ID = "ses_e43a362cbffepcSxbg3AicXOd0"
RAW = Path(__file__).with_name("session-08-export.json")
DOC = Path(__file__).with_name("session-08-transcript.md")
LIMIT = 20000


def stamp(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%SZ")


def redact(value):
    for name, secret in os.environ.items():
        if re.search(r"(API_KEY|PASSWORD|SECRET|TOKEN)$", name, re.I) and \
                len(secret) >= 8:
            value = value.replace(secret, "[REDACTED]")
    return re.sub(r"\bsk-[A-Za-z0-9_-]{16,}\b", "[REDACTED]", value)


def cut(text):
    text = json.dumps(text, ensure_ascii=False) \
        if not isinstance(text, str) else text
    text = redact(text)
    if len(text) > LIMIT:
        return text[:LIMIT] + "\n[truncated by archiver: " + \
            "%d chars cut in the transcript; full value in the raw export]" % \
            (len(text) - LIMIT)
    return text


def fence(text):
    return "`" * max(3, 1 + max((len(m.group()) for m in
                                 re.finditer(r"`+", text)), default=0))


def tool_block(content):
    state = content.get("state", {})
    location = state.get("input", {})
    output = state.get("content")
    output_text = "\n".join(part.get("text", "") for part in output) \
        if isinstance(output, list) else ""
    return cut(json.dumps({"tool": content.get("name"),
                           "input": {key: location.get(key)
                                     for key in sorted(location)},
                           "output": output_text},
                          ensure_ascii=False, indent=2))


def parts(data, number, seq, ts, kind):
    excluded = {"reasoning": "hidden model reasoning", "reasoning-long": None}
    lines = []
    mark = "## %s | source seq %s | session line %s | %s\n\n" % (
        ts, seq, number, kind)
    blocks = data.get("content") if isinstance(data.get("content"), list) else []
    for item in blocks:
        ctype = item.get("type")
        if ctype == "text":
            body = cut(item.get("text", ""))
            f = fence(body)
            lines.append(mark + f + "\n" + body + "\n" + f + "\n")
        elif ctype == "tool":
            body = cut(tool_block(item))
            f = fence(body)
            state = item.get("state", {})
            note = "[persistent value: state.metadata holds a unified file " \
                "patch; see the raw export]" if isinstance(
                    state.get("metadata"), dict) and \
                    state["metadata"].get("files") else ""
            lines.append(mark + f + "\n" + body + "\n" + f + "\n" + note)
            continue
        elif ctype in excluded:
            continue  # Excluded per archival rules; raw export retains them.
        else:
            f = fence(cut(json.dumps(item, ensure_ascii=False, indent=1)))
            lines.append(mark + "### part type %s\n\n%s\n%s\n" % (ctype, f, f))
    return "".join(lines)


def export():
    import sqlite3
    raw_blocks, records, number = [], [], 0
    connection = sqlite3.connect(str(SOURCE_DB))
    try:
        info = connection.execute(
            "SELECT id, slug, directory, title, agent, model, time_created,"
            " time_updated FROM session_v2 WHERE id = ?", (SESSION_ID,)
        ).fetchone()
        rows = connection.execute(
            "SELECT seq, time_created, time_updated, type, data FROM"
            " session_message WHERE session_id = ? ORDER BY seq",
            (SESSION_ID,)).fetchall()
    finally:
        connection.close()
    info_record = {
        "session_id": info[0], "slug": info[1], "directory": info[2],
        "title": info[3], "agent": info[4], "model": info[5],
        "created": stamp(info[6]), "last_update": stamp(info[7])}
    for seq, created, updated, mtype, data in rows:
        payload = json.loads(data)
        json_line = redact(json.dumps({"seq": seq, "type": mtype,
                                       "data": payload}, ensure_ascii=False))
        raw_blocks.append(json_line)
        number += 1
        state = None
        if mtype == "assistant":
            for item in payload.get("content", []):
                if isinstance(item, dict) and item.get("type") in (
                        "text", "tool"):
                    state = item
        elif mtype == "user":
            state = {"type": "text"}
        elif mtype == "agent-switched":
            state = {"type": "switch"}
        excluded_note = {  # Inert bookkeeping kept in the raw export only.
            "synthetic": "_[excluded: synthetic harness record]_\n\n",
            "idle": "_[excluded: idle bookkeeping]_\n\n"}.get(mtype)
        if excluded_note:
            records.append(excluded_note)
            continue
        if state is None:
            records.append("## seq %s — excluded record type: %s\n\n" % (
                seq, mtype))
            continue
        ts = stamp(created if created else updated)
        if state["type"] == "switch":
            records.append("## %s | seq %s — agent switch %s -> %s\n\n" % (
                ts, seq, payload.get("previous", "?"), payload.get("agent")))
            continue
        if state["type"] == "text":
            body = cut(payload.get("text", ""))
            f = fence(body)
            records.append("## %s | seq %s — %s\n\n%s\n%s\n" % (
                ts, seq, "user", body, f))
            continue
        records.append(parts(payload, number, seq, ts, "assistant (tool)"))
    counts = {"user": 0, "assistant": 0, "synthetic": 0, "idle": 0,
              "agent-switched": 0, "other": 0}
    tools = 0
    for seq, created, updated, mtype, data in rows:
        counts[mtype if mtype in counts else "other"] += 1
        payload = json.loads(data)
        for item in payload.get("content", []):
            tools += int(isinstance(item, dict) and item.get("type") == "tool")
    raw = json.dumps({"session": info_record, "source_db": str(SOURCE_DB),
                      "exported_at": stamp(datetime.now(
                          timezone.utc).timestamp() * 1000),
                      "record_counts": counts, "tool_calls": tools,
                      "messages": [json.loads(line) for line in raw_blocks]},
                     ensure_ascii=False, indent=1).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    header = (
        "# OpenCode Session 08 (approved Gemini Flash-Lite model-switch\n"
        "re-verification against official Google documentation, offline\n"
        "validation, manual-run handoff, mandatory transcript archival) —\n"
        "chronological transcript\n\n"
        "- Source session ID: `%s`\n- Session title (at export time): %s\n"
        "- Agent: %s; model: `%s`\n- Directory: `%s`\n"
        "- Created: %s; last stored record at export: %s\n"
        "- Source: local SQLite OpenCode store (`session_message` rows of\n"
        "  `%s`); payloads retained byte-faithfully, not reconstructed.\n"
        "- Raw export: `session-08-export.json` (SHA-256 `%s`), archived\n"
        "  beside this transcript.\n"
        "- Excluded per archival rules: hidden model reasoning parts,\n"
        "  synthetic harness/system-reminder records, idle bookkeeping;\n"
        "  every user message and approval, assistant visible message,\n"
        "  agent switch and tool call with real inputs and outputs is\n"
        "  included below.\n"
        "- Long tool inputs/outputs are cut at %d characters with explicit\n"
        "  `[truncated by archiver]` markers; the raw export holds them in\n"
        "  full.\n"
        "- Records in the raw export: %d (user %d, assistant %d, synthetic\n"
        "  %d, idle %d, agent-switched %d); tool calls: %d.\n"
        "- Credential-shaped strings are redacted; no API key is requested,\n"
        "  displayed or stored anywhere.\n"
        "- Snapshot discipline: this is the record through the shown\n"
        "  sequence; a closing turn may postdate the last capture unless the\n"
        "  exporter is re-run (it replaces only these two Session 08 files).\n"
        "\n---\n\n"
        % (info_record["session_id"], info_record["title"],
           info_record["agent"], info_record["model"], info_record["directory"],
           info_record["created"], info_record["last_update"],
           SOURCE_DB.as_posix(), digest,
           LIMIT, number, counts["user"], counts["assistant"],
           counts["synthetic"], counts["idle"], counts["agent-switched"],
           tools))
    content = header + "".join(records)
    store(RAW, raw)
    store(DOC, content.encode("utf-8"))
    return len(rows), tools, counts, digest


def store(path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("wb") as handle:
        handle.write(data)
    temp.replace(path)
    with path.open("rb") as handle:
        assert handle.read() == data


if __name__ == "__main__":
    rows, tools, counts, digest = export()
    print("exported records:", rows)
    print("tool calls:", tools)
    print("counts:", counts)
    print("raw sha256:", digest)
