"""Explicit H1 synthetic-volume probe; no challenge inputs or HTTP transport.

Run from the project root: python -B -S tests/offline_readiness.py
Not a model-quality benchmark. Reuses the guarded Stage G integration fixture.
"""
import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MODULES = ("data", "llm", "reasoning", "tasks", "validation", "solution")


def verify_imports():
    hashes = {}
    for name in MODULES:
        path = ROOT / (name + ".py")
        ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))
        importlib.import_module(name)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps({"python39_grammar": list(MODULES), "imports": "passed",
                      "site_disabled": bool(sys.flags.no_site), "sha256": hashes}))


def volume(dense):
    from test_solution import IntegrationTests, PipelineTransport
    from test_llm import response
    from llm import Budget
    from unittest.mock import patch
    import reasoning

    class Transport(PipelineTransport):
        def __init__(self):
            super().__init__()
            self.calls = 0
            self.max_wire = 0

        def __call__(self, endpoint, wire, key, timeout):
            self.calls += 1
            self.max_wire = max(self.max_wire, len(wire))
            result = super().__call__(endpoint, wire, key, timeout)
            body = self.requests.pop()  # Avoid retaining mock-only request history.
            if dense and "Extract observations" in body["messages"][0]["content"]:
                packet = json.loads(body["messages"][1]["content"])
                answer = json.loads(json.loads(result[2])["choices"][0]["message"]["content"])
                for span in packet["primary"]:
                    if span["message_id"] != "M1":
                        answer["observations"].append({
                            "kind": "person", "subjects": ["P1"],
                            "meaning": "Synthetic colleague evidence",
                            "evidence": [{k: span[k] for k in ("message_id", "start", "end", "text")}],
                        })
                result = response(json.dumps(answer))
            return result

    fixture = IntegrationTests()
    fixture.setUp()
    try:
        chats = [{"chat_id": "C" + str(i), "is_group": True, "name": "Synthetic group",
                  "participants": ["ME", "P1"]} for i in range(1, 61)]
        (fixture.folder / "chats.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in chats), encoding="utf-8")
        with (fixture.folder / "messages.jsonl").open("w", encoding="utf-8") as stream:
            for i in range(1, 15001):
                body = ("P1 is my colleague. Synthetic routine discussion with explicit source text. " * 2)
                if i == 1:
                    body = "I own Synthetic company, P1 is a colleague. I aim to practice writing. I will draft a report."
                if i == 2:
                    body *= 100  # One 15,000-character message exercises span splitting.
                row = {"id": "M" + str(i), "chat_id": "C1" if i <= 3000 else "C" + str(2 + i % 59),
                       "sender_id": "ME", "sender_name": "User", "ts": i,
                       "kind": "text", "body": body, "quoted_id": None}
                stream.write(json.dumps(row) + "\n")
        input_bytes = sum((fixture.folder / name).stat().st_size for name in
                          ("messages.jsonl", "chats.jsonl", "seed.json"))
        transport = Transport()
        packet_bytes = {}
        packet_counts = {}
        original_call = reasoning._call
        def measured_call(client, stage, packet, validate, limit):
            packet_bytes[stage] = max(packet_bytes.get(stage, 0), len(reasoning._encoded(packet)))
            packet_counts[stage] = packet_counts.get(stage, 0) + 1
            return original_call(client, stage, packet, validate, limit)
        tracemalloc.start()
        started = time.perf_counter()
        # The small integration fixture plans only 30 calls. This synthetic
        # workload explicitly plans up to 10,000; no provider is involved.
        with patch("test_solution.Budget", side_effect=lambda **kw: Budget(planned_base_calls=10000)), \
                patch.object(reasoning, "_call", side_effect=measured_call):
            status, summary = fixture.run_pipeline(transport)
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        states = {k: v["state"] for k, v in summary.get("stages", {}).items()}
        preserved = fixture.output.read_text() == "old output"
        output_hash = hashlib.sha256(fixture.output.read_bytes()).hexdigest()
        result = {"fixture": "dense" if dense else "sparse", "messages": 15000,
                  "chats": 60, "people": 1, "large_chat_messages": 3000,
                  "input_bytes": input_bytes, "seconds": round(elapsed, 3),
                  "peak_traced_python_bytes": peak, "fake_calls": transport.calls,
                  "max_request_bytes": transport.max_wire, "exit_status": status,
                  "max_context_packet_bytes": packet_bytes,
                  "context_packet_counts": packet_counts,
                  "state": summary.get("state"), "stages": states,
                  "prior_output_preserved": preserved}
        result["output_sha256"] = output_hash
        print(json.dumps(result), flush=True)
        assert status == 0 and summary["state"] == "succeeded", result
        assert packet_bytes["entities"] <= 100000, result
        entities = summary["stages"]["entities"]
        assert entities["required_batches"] == entities["completed_batches"]
        original = summary["stages"]["extraction"]["observations"]
        assert entities["evidence_registry"] == {o["id"]: o for o in original}
        reviewed = {i for p in entities["partitions"].values() for i in p["observations"]}
        assert reviewed == set(entities["evidence_registry"])
        targets = {tuple(t) for p in entities["partitions"].values() for t in p["targets"]}
        assert len(targets) == 61
        for target in targets:
            reviewed = {i for p in entities["partitions"].values() if target in p["targets"]
                        for i in p["observations"]}
            assert reviewed == set(entities["evidence_registry"])
        if dense:
            assert packet_counts["entities"] > 2, result
        return output_hash
    finally:
        fixture.doCleanups()


if __name__ == "__main__":
    verify_imports()
    sparse = volume(dense=False)
    dense = volume(dense=True)
    assert sparse == dense, "Equivalent synthetic decisions must produce identical output"
