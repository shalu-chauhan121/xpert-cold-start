"""Session-08 offline tests for bounded, privacy-safe response capture.

Regressions for the Session-08 diagnostic addition: every settled pilot
attempt records ONE bounded response-side capture (structured response
bodies, stage/job identifiers, finish reasons, HTTP status, local
validation outcomes) so future `validation` vs `malformed_content` run
failures are precisely diagnosable and Gate 7 semantic review has the real
synthetic-only model text. Never captured: request/wire bodies, transport
headers, credentials, endpoints, or provider error pages for non-2xx
responses. No network; no credentials; synthetic values only.
"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "tests"))
sys.path.insert(0, str(PROJECT / "tests" / "pilot_fixtures"))

import llm
import pilot_runner
from pilot_runner import run_pilot
from mock_responses import respond
from test_llm import Clock

ENV = {"LLM_BASE_URL": "https://synthetic.invalid/v1/",
       "LLM_MODEL": "synthetic-v1", "LLM_API_KEY": "synthetic-secret"}
PILOT_ENV = {"LLM_BASE_URL": "https://synthetic.invalid/v1/",
             "LLM_MODEL": "synthetic-offline",
             "LLM_API_KEY": "synthetic-offline-key"}
PRICING = {"model": "synthetic-mock-1", "source": "offline projection only",
           "currency": "USD", "input_usd_per_mtok": 0.75,
           "output_usd_per_mtok": 3.75}
REQUEST_SENTINEL = "REQUEST-SIDE-SENTINEL-never-captured-message-text"


def chat_json(content, finish="stop", **extra):
    data = {"choices": [{"finish_reason": finish,
                         "message": {"content": content}}],
            "model": "synthetic-v1",
            "usage": {"prompt_tokens": 12, "completion_tokens": 8,
                      "total_tokens": 20}}
    data.update(extra)
    return json.dumps(data).encode("utf-8")


class CaptureSeamTests(unittest.TestCase):
    """Unit-level Client capture regressions (opt-in; default disabled)."""

    def setUp(self):
        self.records = []
        self.enter = {}

    def client(self, transport, capture=None, capture_max_bytes=4096,
               **extra):
        with patch.dict(os.environ, ENV, clear=True):
            return llm.Client(transport=transport, clock=Clock(),
                              sleep=Clock().sleep, capture=capture,
                              capture_max_bytes=capture_max_bytes, **extra)

    def chat(self, transport, validate=None, cap=None, client=None):
        if client is None:
            client = self.client(transport, capture=self.records.append,
                                 capture_max_bytes=cap or 4096)
        with patch.dict(os.environ, ENV, clear=True):
            messages = [{"role": "user", "content": REQUEST_SENTINEL}]
            kwargs = {"validate": validate} if validate else {}
            return client.request(messages, None, None, 30,
                                  {"type": "json_object"}, 6, **kwargs)

    def test_default_client_captures_nothing(self):
        transport = lambda *a: (200, {}, chat_json('{"a": 1}/>'))
        # Default (capture=None): no callback exists and no change occurs.
        with patch.dict(os.environ, ENV, clear=True):
            base = llm.Client(transport=transport, clock=Clock(),
                              sleep=Clock().sleep)
        self.assertIsNone(base.capture)
        self.assertEqual(base.capture_failures, 0)

    def test_successful_structured_response_captured_with_identifiers(self):
        self.chat(lambda *a: (200, {}, chat_json('{"a": 1}')))
        self.assertEqual(len(self.records), 1)
        record = self.records[0]
        self.assertEqual(record["outcome"], "success")
        self.assertEqual(record["http_status"], None)
        self.assertEqual(record["finish_reason"], "stop")
        self.assertEqual(record["model"], "synthetic-v1")
        self.assertIsNone(record["error_detail"])
        self.assertFalse(record["body_truncated"])
        self.assertEqual(record["body_bytes"], len(chat_json('{"a": 1}')))
        # The body is the provider envelope itself (escaped inner JSON).
        self.assertIn("choices", record["body_text"])
        self.assertIn("finish_reason", record["body_text"])
        self.assertEqual(record["content_text"], '{"a": 1}')
        self.assertEqual(record["attempt"], 1)
        self.assertFalse(record["retry"])

    def test_secret_headers_endpoint_and_request_never_captured(self):
        # Even with a plain synthetic provider reply, no request-side state
        # (user message text, wire body, endpoint, key, headers) may appear
        # in any capture field; only response-side fields exist by design.
        self.chat(lambda *a: (200, {}, chat_json('{"a": 1}')))
        record = self.records[0]
        self.assertEqual(set(record), {
            "job_id", "context", "attempt", "recovery", "retry", "outcome",
            "http_status", "finish_reason", "model", "error_detail",
            "body_bytes", "body_sha256", "body_truncated", "body_text",
            "content_text", "content_truncated"})
        self.assertNotIn(REQUEST_SENTINEL, json.dumps(record))
        self.assertNotIn(ENV["LLM_API_KEY"], json.dumps(record))
        self.assertNotIn("https://synthetic.invalid", json.dumps(record))
        self.assertEqual(record["context"], {})

    def test_size_cap_truncates_body_keeps_full_sha256(self):
        payload = chat_json('{"a": "' + "x" * 9000 + '"}')
        self.chat(lambda *a: (200, {}, payload), cap=128)
        record = self.records[0]
        self.assertTrue(record["body_truncated"])
        self.assertEqual(len(record["body_text"].encode("utf-8")) <= 128,
                         True)
        import hashlib
        self.assertEqual(record["body_sha256"],
                         hashlib.sha256(payload).hexdigest())
        self.assertEqual(record["body_bytes"], len(payload))

    def test_malformed_and_validation_outcomes_captured(self):
        # malformed_content: non-JSON prose under json_object format.
        with self.assertRaises(llm.LLMError):
            self.chat(lambda *a: (200, {}, chat_json('not json at all')))
        record = self.records[-1]
        self.assertEqual(record["outcome"], "malformed_content")
        self.assertIn("does not satisfy", record["error_detail"])
        self.assertIn("not json at all", record["body_text"])
        # A wrapped JSON object passes the shared parse but can still fail
        # the stage validator: the local exception class is in the detail.
        def validate(_text):
            raise RuntimeError("Invalid organisation group")
        with self.assertRaises(llm.LLMError):
            self.chat(lambda *a: (200, {}, chat_json('{"a": 1}')),
                      validate=validate)
        record = self.records[-1]
        self.assertEqual(record["outcome"], "validation")
        self.assertIn("(RuntimeError)", record["error_detail"])
        self.assertEqual(record["content_text"], '{"a": 1}')

    def test_http_error_pages_never_captured_but_status_recorded(self):
        with self.assertRaises(llm.LLMError):
            self.chat(lambda *a: (503, {}, json.dumps(
                {"error": {"code": 503, "message": "UNAVAILABLE"}}).encode()))
        record = self.records[-1]
        self.assertEqual(record["outcome"], "http_error")
        self.assertEqual(record["http_status"], 503)
        self.assertIsNone(record["body_text"])
        self.assertIsNone(record["body_bytes"])
        self.assertIsNone(record["body_sha256"])

    def test_retry_attempt_flags_recorded(self):
        calls = {"n": 0}

        def flaky(endpoint, wire, key, timeout):
            calls["n"] += 1
            if calls["n"] == 1:
                return 429, {"Retry-After": "1"}, json.dumps(
                    {"error": {"code": 429}}).encode("utf-8")
            return 200, {}, chat_json('{"a": 2}')

        client = self.client(flaky, capture=self.records.append,
                             budget=llm.Budget(planned_base_calls=5))
        self.chat(flaky, client=client)
        self.assertEqual(len(self.records), 2)
        first, second = self.records
        self.assertEqual(first["outcome"], "http_error")
        self.assertEqual(first["http_status"], 429)
        self.assertFalse(first["retry"])
        self.assertEqual(second["retry"], True)
        self.assertEqual(second["attempt"], 2)
        self.assertEqual(second["outcome"], "success")

    def test_capture_failure_never_breaks_dispatch(self):
        def broken(_record):
            raise RuntimeError("capture sink failed")
        with patch.dict(os.environ, ENV, clear=True):
            client = llm.Client(
                transport=lambda *a: (200, {}, chat_json('{"a": 3}')),
                clock=Clock(), sleep=Clock().sleep, capture=broken)
            result = client.chat([{"role": "user", "content": "synthetic"}],
                                 None, None, 30, {"type": "json_object"}, 6)
        self.assertEqual(result, '{"a": 3}')
        self.assertEqual(client.capture_failures, 1)

    def test_capture_context_allowlist_only(self):
        with patch.dict(os.environ, ENV, clear=True):
            client = llm.Client(
                transport=lambda *a: (200, {}, chat_json('{"a": 4}')),
                clock=Clock(), sleep=Clock().sleep,
                capture=self.records.append)
            client.request([{"role": "user", "content": "synthetic"}],
                           None, None, 30, {"type": "json_object"}, 6,
                           job_id="x:y",
                           cache_context={"stage": "organisations",
                                          "prompt_version": "context-3",
                                          "secret_field": "SECRET",
                                          "schema_version": 1,
                                          "nested": {"deep": []}})
        record = self.records[0]
        self.assertEqual(record["job_id"], "x:y")
        self.assertEqual(record["context"], {"stage": "organisations",
                                             "prompt_version": "context-3",
                                             "schema_version": 1})
        self.assertNotIn("SECRET", json.dumps(record))


class PilotCaptureTests(unittest.TestCase):
    def _offline(self, transport, capture_path, overwrite_refusal=False):
        captured_out = io.StringIO()
        with patch.dict(os.environ, PILOT_ENV, clear=True), \
                redirect_stdout(captured_out):
            document = run_pilot(mode="test", transport=transport,
                                 clock=Clock(), sleep=Clock().sleep,
                                 verified_pricing=PRICING,
                                 capture_path=capture_path)
        self.assertNotIn(PILOT_ENV["LLM_API_KEY"], captured_out.getvalue())
        return document

    def test_full_offline_run_captures_every_attempt(self):
        import tempfile
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        os.unlink(path)
        try:
            document = self._offline(respond, path)
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        finally:
            if Path(path).exists():
                os.unlink(path)
        self.assertEqual(document["run_state"], "completed")
        self.assertEqual(document["planned"], 25)
        self.assertEqual(document["budget_summary"]["attempts"], 25)
        self.assertEqual(payload["capture_count"], 25)
        self.assertEqual(len(payload["captures"]), 25)
        self.assertEqual(payload["capture_failures"], 0)
        self.assertTrue(payload["synthetic_only"])
        # One capture per settled transmission; no extras, no cache hits.
        self.assertEqual(len(payload["captures"]),
                         document["budget_summary"]["attempts"])
        # Evidence references the capture artifact additively.
        self.assertEqual(document["response_captures"]["path"],
                         Path(path).name)
        self.assertEqual(document["response_captures"]["count"], 25)
        self.assertEqual(document["synthetic_only"], True)

    def test_capture_artifact_redaction_full_run(self):
        import tempfile
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        os.unlink(path)
        try:
            self._offline(respond, path)
            text = Path(path).read_text(encoding="utf-8")
        finally:
            if Path(path).exists():
                os.unlink(path)
        # Credentials, endpoint or request-side texts never reach the file.
        self.assertNotIn(PILOT_ENV["LLM_API_KEY"], text)
        self.assertNotIn("synthetic.invalid", text)
        self.assertNotIn("messages", text.split('"purpose"')[0])

    def test_existing_capture_file_refused_without_run(self):
        import tempfile
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        with open(path, "a", encoding="utf-8") as fp:
            fp.write("prior\n")
        try:
            document = self._offline(respond, path)
        finally:
            os.unlink(path)
        self.assertEqual(document["run_state"], "refused")
        self.assertEqual(document["error_code"], "capture_exists")
        self.assertIn("never overwritten", document["message"])

    def test_same_path_for_evidence_and_captures_refused(self):
        import tempfile
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        os.unlink(path)
        try:
            document = self._offline(respond, path)
        finally:
            pass
        with patch.dict(os.environ, PILOT_ENV, clear=True):
            refused = run_pilot(mode="test", transport=respond,
                                clock=Clock(), sleep=Clock().sleep,
                                verified_pricing=PRICING,
                                evidence_path=path, capture_path=path)
        self.assertEqual(refused["run_state"], "refused")
        self.assertEqual(refused["error_code"], "configuration")

    def test_capture_refusal_does_not_dispatch_single_job(self):
        import tempfile
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        with open(path, "a", encoding="utf-8") as fp:
            fp.write("prior\n")
        calls = []
        try:
            with patch.dict(os.environ, PILOT_ENV, clear=True):
                document = run_pilot(
                    mode="test", transport=lambda *a: calls.append(1),
                    clock=Clock(), sleep=Clock().sleep,
                    verified_pricing=PRICING, capture_path=path)
        finally:
            os.unlink(path)
        self.assertEqual(document["error_code"], "capture_exists")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
