"""Export only actual public dialogue/tool records from this session's local log."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

SOURCE = Path('C:/Users/Shalu Chauhan/.codex/sessions/2026/11/05/rollout-2026-11-05T20-06-13-01a1ac23-8d6d-7a70-9d3d-98e235cccf20.jsonl')
DEST = Path(__file__).with_name('session-13-transcript.md')


def export():
    raw = SOURCE.read_bytes()
    lines = raw.splitlines(keepends=True)
    blocks = []
    final_seen = False
    session_started = False
    for number, line in enumerate(lines, 1):
        try:
            record = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            break  # A concurrent append may leave an unfinished last line.
        payload = record.get('payload', {})
        kind = payload.get('type', '')
        if record.get('type') == 'response_item' and kind == 'message' and payload.get('role') == 'user':
            message = ''.join(part.get('text', '') for part in payload.get('content', []))
            if message.startswith('Complete the remaining XPERT Cold Start H1 readiness work'):
                session_started = True
        if not session_started:
            continue
        include = False
        if record.get('type') == 'response_item':
            include = (kind == 'message' and payload.get('role') in ('user', 'assistant')) or kind in (
                'function_call', 'function_call_output', 'custom_tool_call', 'custom_tool_call_output')
            final_seen |= kind == 'message' and payload.get('role') == 'assistant' and payload.get('phase') in ('final', 'final_answer')
        elif record.get('type') == 'event_msg' and kind == 'item_completed':
            item = payload.get('item', {})
            include = item.get('type') in ('commandExecution', 'fileChange', 'CommandExecution', 'FileChange')
        if kind == 'message' and payload.get('role') == 'user':
            final_seen = False
        if kind == 'message' and (payload.get('channel') == 'analysis' or payload.get('phase') == 'analysis'):
            include = False
        if include:
            value = json.dumps(payload, ensure_ascii=False, indent=2)
            # Redact known credential shapes and actual configured credential values.
            for name, secret in os.environ.items():
                if re.search(r'(API_KEY|PASSWORD|SECRET|TOKEN)$', name, re.I) and len(secret) >= 8:
                    value = value.replace(secret, '[REDACTED]')
            value = re.sub(r'\bsk-[A-Za-z0-9_-]{16,}\b', '[REDACTED]', value)
            fence = '`' * max(3, 1 + max((len(m.group()) for m in re.finditer(r'`+', value)), default=0))
            blocks.append(f"## {record.get('timestamp', '')} | source line {number} | {kind}\n\n{fence}json\n{value}\n{fence}\n")
    header = ('# Session 13 actual conversation transcript\n\n'
              f'Source: `{SOURCE}`\n\n'
              f'Snapshot SHA-256: `{hashlib.sha256(raw).hexdigest()}`\n\n'
              'Chronological export of original recorded user/assistant messages and tool calls/outputs. '
              'Payloads are retained, not reconstructed. Supplemental command/file events are included when present. '
              'Internal reasoning, system/developer instructions, telemetry, duplicate UI dialogue and replacement summaries are excluded. '
              'Recorded truncation remains truncation; missing output is not invented. Credential values are redacted. '
              'Export begins at the actual Session 13 H1 task prompt; preceding session records are excluded. '
              'Earlier session transcripts are untouched.\n\n')
    header += (f'Exported records: {len(blocks)}. Last exported record: '
               f'{blocks[-1].splitlines()[0] if blocks else chr(45)}.\n\n'
               f'Latest user turn final reply present: {final_seen}. '
               'This is a snapshot; later records are absent until refreshed.\n\n')
    content = header + '\n'.join(blocks)
    temp = DEST.with_suffix('.tmp')
    temp.write_text(content, encoding='utf-8')
    temp.replace(DEST)
    assert DEST.read_text(encoding='utf-8') == content
    return len(blocks), final_seen


if __name__ == '__main__':
    if '--watch' in sys.argv:
        end = time.monotonic() + 600
        while time.monotonic() < end:
            count, final_seen = export()
            if final_seen:
                print(f'Exported {count} records including actual final response.', flush=True)
                break
            time.sleep(1)
    else:
        print(export())
