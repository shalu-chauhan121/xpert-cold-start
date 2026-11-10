"""Stage D offline synthetic tests. No challenge data, credentials or API calls."""
import ast
import base64
import copy
import inspect
import io
import json
import multiprocessing
import os
from pathlib import Path
import socket
import ssl
import struct
import sys
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import llm


ENV = {"LLM_BASE_URL": "https://synthetic.invalid/v1/",
       "LLM_MODEL": "synthetic-v1", "LLM_API_KEY": "synthetic-secret"}
MESSAGES = [{"role": "user", "content": "Synthetic नमस्ते বাংলা"}]


class Clock:
    def __init__(self):
        self.now = 0.0
        self.waits = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def response(content="synthetic reply", usage=True, finish="stop", **extra):
    data = {"choices": [{"finish_reason": finish, "message": {"content": content}}],
            "model": "synthetic-v1", "system_fingerprint": "synthetic-revision"}
    if usage is True:
        data["usage"] = {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}
    elif usage is not False:
        data["usage"] = usage
    data.update(extra)
    return 200, {}, json.dumps(data).encode("utf-8")


class FakeTransport:
    def __init__(self, *results):
        self.results = list(results or [response()])
        self.calls = []

    def __call__(self, endpoint, body, key, timeout):
        self.calls.append((endpoint, json.loads(body), key, timeout))
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        if callable(result):
            return result()
        return result


# Module-level spawn targets; all are synthetic and contain no networking.
def hang_worker(buffer, endpoint, body, key, timeout, max_bytes):
    time.sleep(60)


def partial_worker(buffer, endpoint, body, key, timeout, max_bytes):
    buffer[:8] = struct.pack("!Q", 1000)
    buffer[8:10] = b"{\""
    time.sleep(60)


def crash_worker(buffer, endpoint, body, key, timeout, max_bytes):
    os._exit(7)


def empty_worker(buffer, endpoint, body, key, timeout, max_bytes):
    return


def success_worker(buffer, endpoint, body, key, timeout, max_bytes):
    llm._write_worker_result(buffer, {"status": 200, "retry_after": "",
                                    "body": base64.b64encode(response()[2]).decode("ascii")})


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, ENV, clear=True))
        # A mistakenly invoked real transport must fail before DNS/connect.
        self.enterContext(patch.object(socket, "getaddrinfo", side_effect=AssertionError("No network")))
        self.enterContext(patch.object(socket.socket, "connect", side_effect=AssertionError("No network")))
        self.clock = Clock()

    # unittest.enterContext was introduced after Python 3.9; keep tests runnable
    # on the target interpreter as well as parsing with its grammar.
    def enterContext(self, manager):
        value = manager.__enter__()
        self.addCleanup(manager.__exit__, None, None, None)
        return value

    def client(self, *results, **kwargs):
        self.transport = FakeTransport(*results)
        return llm.Client(transport=self.transport, clock=self.clock,
                          sleep=self.clock.sleep, **kwargs)

    def fails(self, code, operation):
        with self.assertRaises(llm.LLMError) as caught:
            operation()
        self.assertEqual(caught.exception.detail["code"], code, caught.exception.detail)
        return caught.exception

    def test_environment_and_request_compatibility(self):
        client = self.client(response('{"ok":true}'))
        self.assertEqual(client.chat(MESSAGES, "override", 0.4, 30,
                                     {"type": "json_object"}, 6), '{"ok":true}')
        endpoint, body, key, timeout = self.transport.calls[0]
        self.assertEqual(endpoint, "https://synthetic.invalid/v1/chat/completions")
        self.assertEqual(body, {"model": "override", "messages": MESSAGES,
                               "temperature": 0.4, "max_tokens": 30,
                               "response_format": {"type": "json_object"}})
        self.assertEqual(key, ENV["LLM_API_KEY"])
        self.assertEqual(timeout, 6)
        self.assertEqual(client.last_metadata["system_fingerprint"], "synthetic-revision")

    def test_default_completion_is_reserved_and_sent(self):
        client = self.client(default_completion_tokens=37)
        client.chat(MESSAGES)
        self.assertEqual(self.transport.calls[0][1]["max_tokens"], 37)
        self.assertEqual(client.budget.records[0]["reserved_completion_tokens"], 37)

    def test_public_signature_and_positional_wrapper(self):
        # The temperature parameter stays in the signature; its None default is
        # resolved model-specifically (Gemini 3+ omitted, others 0) in
        # Client.request, per the approved Session 05 correction.
        self.assertEqual(str(inspect.signature(llm.chat)),
                         "(messages, model=None, temperature=None, max_tokens=None, response_format=None, timeout=120)")
        client = self.client()
        with patch.object(llm, "_default_client", client):
            self.assertEqual(llm.chat(MESSAGES, None, 0, 64, None, 10), "synthetic reply")

    def test_default_temperature_is_model_specific(self):
        """Regression (approved Session 05 correction): Gemini 3+ models omit
        the deprecated field by default; every other model keeps the prior
        explicit default of 0. Explicit finite numbers are unchanged for both.
        Unique message text per dispatch avoids response-cache collisions."""
        def probe(tag):
            return [{"role": "user", "content": "Probe %s" % tag}]
        client = self.client(response(), response(), response(), response(),
                             response(), response())
        client.chat(probe("default-synthetic"))  # env model synthetic-v1
        self.assertEqual(self.transport.calls[0][1]["temperature"], 0)
        client.chat(probe("pilot-gemini35-lite"), model="gemini-3.5-flash-lite")
        self.assertNotIn("temperature", self.transport.calls[1][1])
        client.chat(probe("gemini-pro"), model="Gemini-3-Pro")  # case-insensitive
        self.assertNotIn("temperature", self.transport.calls[2][1])
        client.chat(probe("gemini-explicit"), model="gemini-3.5-flash-lite",
                    temperature=0.2)
        self.assertEqual(self.transport.calls[3][1]["temperature"], 0.2)
        client.chat(probe("legacy-explicit"), temperature=0)
        self.assertEqual(self.transport.calls[4][1]["temperature"], 0)
        # The pilot path resolves the model from the environment as well.
        with patch.dict(os.environ, {"LLM_MODEL": "gemini-3.5-flash-lite"}):
            client.chat(probe("env-gemini"))
        self.assertNotIn("temperature", self.transport.calls[5][1])

    def test_default_wrapper_environment_budget(self):
        with patch.dict(os.environ, {"LLM_TOKEN_CEILING": "500", "LLM_PLANNED_BASE_CALLS": "10"}), \
                patch.object(llm, "_default_client", None), \
                patch.object(llm, "ProcessTransport", return_value=FakeTransport()):
            llm.chat(MESSAGES, max_tokens=10)
            self.assertEqual(llm._default_client.budget.token_ceiling, 500)
            self.assertEqual(llm._default_client.budget.recovery_limit, 2)

    def test_invalid_configuration_fails_before_transport(self):
        for name in ENV:
            with self.subTest(name=name), patch.dict(os.environ, {name: ""}):
                client = self.client()
                self.fails("configuration", lambda: client.chat(MESSAGES))
                self.assertEqual(self.transport.calls, [])
        for url in ("ftp://synthetic.invalid", "https://user:secret@synthetic.invalid",
                    "https://synthetic.invalid/?key=secret", "https://synthetic.invalid/#secret",
                    "https://synthetic.invalid:bad", "https://synthetic.invalid/\n"):
            with self.subTest(url=url), patch.dict(os.environ, {"LLM_BASE_URL": url}):
                self.fails("configuration", lambda: self.client().chat(MESSAGES))

    def test_invalid_generation_settings(self):
        for settings in ({"max_tokens": 0}, {"max_tokens": -1}, {"max_tokens": True},
                         {"timeout": 0}, {"timeout": float("inf")}, {"temperature": float("nan")},
                         {"response_format": "json"}, {"model": ""}):
            with self.subTest(settings=settings):
                self.fails("configuration", lambda: self.client().chat(MESSAGES, **settings))
        self.fails("configuration", lambda: self.client().chat([]))
        self.fails("configuration", lambda: self.client().chat([{"role": "user"}]))

    def test_empty_malformed_missing_and_incomplete_responses(self):
        cases = [(response(""), "empty"), (response(" \n"), "empty"),
                 ((200, {}, b"not-json"), "malformed"), ((200, {}, b"\xff"), "malformed"),
                 ((200, {}, b'{}'), "incomplete"), ((200, {}, b'[]'), "malformed"),
                 ((200, {}, b'{"choices":[],"choices":[]}'), "malformed"),
                 (response(None), "incomplete"), (response(finish=None), "incomplete"),
                 (response(finish="tool_calls"), "incomplete")]
        for result, code in cases:
            with self.subTest(code=code, result=result):
                client = self.client(result)
                self.fails(code, lambda: client.chat(MESSAGES))
                self.assertEqual(client.cache, {})
                self.assertEqual(len(self.transport.calls), 1)

    def test_truncation_discarded_with_split_signal(self):
        client = self.client(response('{"partial":', finish="length"),
                             budget=llm.Budget(planned_base_calls=100))
        error = self.fails("truncated", lambda: client.chat(MESSAGES))
        self.assertTrue(error.detail["split_recommended"])
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(client.cache, {})
        self.assertEqual(client.budget.summary()["charged_tokens"], 20)

    def test_refusal_and_content_filter(self):
        refused = {"choices": [{"finish_reason": "stop",
                                "message": {"content": None, "refusal": "private refusal text"}}]}
        for result in ((200, {}, json.dumps(refused).encode()), response(finish="content_filter")):
            client = self.client(result)
            error = self.fails("refused", lambda: client.chat(MESSAGES))
            self.assertNotIn("private refusal", str(error.detail))
            self.assertEqual(client.cache, {})

    def test_json_content_and_caller_completeness_validation(self):
        for content in ('{"a":', '[]', '{"a":NaN}', '{"a":1,"a":2}'):
            client = self.client(response(content))
            self.fails("malformed_content", lambda: client.chat(MESSAGES, response_format={"type": "json_object"}))
        client = self.client(response('{"items":[]}'))
        self.fails("validation", lambda: client.request(MESSAGES, validate=lambda text: bool(json.loads(text)["items"])))
        self.assertEqual(client.cache, {})

    def test_missing_and_partial_usage_retains_reservation(self):
        for usage in (False, None, {}, {"prompt_tokens": 12}, {"completion_tokens": 8},
                      {"total_tokens": 9999}, {"prompt_tokens": -2, "completion_tokens": True}):
            with self.subTest(usage=usage):
                client = self.client(response(usage=usage))
                client.chat(MESSAGES, max_tokens=40)
                record = client.budget.records[0]
                self.assertTrue(record["unknown_usage"])
                self.assertFalse(record["outstanding"])
                expected = ((record["reported_prompt_tokens"] if record["reported_prompt_tokens"] is not None
                             else record["estimated_prompt_tokens"]) +
                            (record["reported_completion_tokens"] if record["reported_completion_tokens"] is not None else 40))
                self.assertEqual(record["charged_tokens"], max(expected, record["reported_total_tokens"] or 0))
                self.assertGreater(client.budget.summary()["unknown_usage_reservations"], 0)

    def test_reported_categories_not_double_counted(self):
        usage = {"prompt_tokens": 20, "completion_tokens": 30, "total_tokens": 50,
                 "prompt_tokens_details": {"cached_tokens": 10, "audio_tokens": 2},
                 "completion_tokens_details": {"reasoning_tokens": 25, "audio_tokens": 1,
                                               "accepted_prediction_tokens": 3, "rejected_prediction_tokens": 2}}
        client = self.client(response(usage=usage))
        client.chat(MESSAGES)
        self.assertEqual(client.budget.summary()["charged_tokens"], 50)
        self.assertEqual(len(client.budget.records[0]["additional_usage"]), 6)
        self.assertIsNone(client.budget.summary()["dollar_cost"])

    def test_estimator_calibrates_upward_and_never_downward(self):
        client = self.client(response(usage={"prompt_tokens": 2000, "completion_tokens": 5}), response())
        client.chat(MESSAGES)
        factor = client.budget.safety_factor
        self.assertGreater(factor, 1)
        client.chat([{"role": "user", "content": "another"}])
        self.assertGreater(client.budget.records[1]["estimated_prompt_tokens"],
                           client.budget.records[1]["raw_prompt_estimate"])
        self.assertEqual(client.budget.safety_factor, factor)

    def test_temporary_http_then_success_with_backoff(self):
        client = self.client((429, {"Retry-After": "3"}, b"private error"), response(),
                             budget=llm.Budget(planned_base_calls=5))
        self.assertEqual(client.chat(MESSAGES), "synthetic reply")
        self.assertEqual(self.clock.waits, [3])
        self.assertEqual(client.budget.summary()["recoveries"], 1)
        self.assertEqual(client.budget.summary()["wait"], 3)
        self.assertTrue(client.budget.records[0]["unknown_usage"])

    def test_persistent_failures_maximum_three_transmissions(self):
        client = self.client(*[(503, {}, b"private") for _ in range(4)],
                             budget=llm.Budget(planned_base_calls=100))
        self.fails("http_error", lambda: client.request(MESSAGES, job_id="original"))
        self.assertEqual(len(self.transport.calls), 3)
        self.assertEqual(self.clock.waits, [1, 2])
        self.assertEqual(client.budget.jobs["original"], 3)

    def test_shared_twenty_percent_cap_and_no_unplanned_retries(self):
        for planned, expected in ((None, 1), (4, 1), (5, 2)):
            with self.subTest(planned=planned):
                client = self.client(*[(500, {}, b"")] * 4,
                                     budget=llm.Budget(planned_base_calls=planned))
                self.fails("http_error", lambda: client.chat(MESSAGES))
                self.assertEqual(len(self.transport.calls), expected)
        budget = llm.Budget(planned_base_calls=5)
        client = self.client((500, {}, b""), response(), (500, {}, b""), budget=budget)
        client.request(MESSAGES, job_id="a")
        self.fails("http_error", lambda: client.request(MESSAGES, job_id="b", cache_context={"input": "changed"}))
        self.assertEqual(budget.recoveries, 1)

    def test_future_children_share_original_transmission_allowance(self):
        client = self.client(response(finish="length"), response(), response(),
                             budget=llm.Budget(planned_base_calls=10))
        self.fails("truncated", lambda: client.request(MESSAGES, job_id="root"))
        client.request(MESSAGES, job_id="root", cache_context={"child": 1})
        client.request(MESSAGES, job_id="root", cache_context={"child": 2})
        self.fails("attempt_limit", lambda: client.request(MESSAGES, job_id="root", cache_context={"child": 3}))
        self.assertEqual(len(self.transport.calls), 3)
        self.assertEqual(client.budget.recoveries, 2)

    def test_authentication_and_permanent_errors_never_retry(self):
        for status in (301, 400, 401, 403, 404, 413, 422):
            with self.subTest(status=status):
                client = self.client((status, {}, b"secret private prompt"),
                                     budget=llm.Budget(planned_base_calls=100))
                error = self.fails("authentication" if status in (401, 403) else "http_error",
                                   lambda: client.chat(MESSAGES))
                self.assertEqual(len(self.transport.calls), 1)
                self.assertNotIn("secret", str(error.detail))
                self.assertEqual(client.budget.recoveries, 0)

    def test_network_errors_and_timeouts_are_unknown_not_free(self):
        for failure in (TimeoutError("private"), urllib.error.URLError("private"),
                        llm.LLMError("timeout", "Request deadline reached.", True)):
            client = self.client(failure, response(), budget=llm.Budget(planned_base_calls=5))
            client.chat(MESSAGES, max_tokens=10)
            record = client.budget.records[0]
            self.assertTrue(record["unknown_usage"])
            self.assertEqual(record["charged_tokens"], record["estimated_prompt_tokens"] + 10)
            self.assertGreater(client.budget.summary()["charged_tokens"], 20)

    def test_retry_after_too_long_stops_without_early_retry(self):
        client = self.client((429, {"Retry-After": "60"}, b""), budget=llm.Budget(planned_base_calls=10))
        self.fails("retry_delay", lambda: client.chat(MESSAGES))
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(self.clock.waits, [])

    def test_network_cutoff_and_exit_target(self):
        deadline = llm.Deadline(self.clock)
        self.assertEqual((deadline.network, deadline.exit_target, deadline.overall), (1620, 1770, 1800))
        client = self.client(deadline=deadline)
        self.clock.now = 1620
        self.fails("deadline", lambda: client.chat(MESSAGES))
        self.assertEqual(self.transport.calls, [])
        deadline.check(finalizing=True)
        self.clock.now = 1770
        self.fails("exit_deadline", lambda: deadline.check(finalizing=True))

    def test_timeout_clamped_to_network_time_remaining(self):
        client = self.client()
        self.clock.now = 1618
        client.chat(MESSAGES, timeout=120)
        self.assertEqual(self.transport.calls[0][3], 2)

    def test_response_arriving_after_cutoff_is_not_success(self):
        def late():
            self.clock.now = 1621
            return response()
        client = self.client(late)
        self.fails("deadline", lambda: client.chat(MESSAGES))
        self.assertEqual(client.cache, {})
        self.assertTrue(client.budget.records[0]["unknown_usage"])

    def test_response_arriving_after_attempt_timeout_is_not_success(self):
        def late():
            self.clock.now += 11
            return response()
        client = self.client(late)
        self.fails("timeout", lambda: client.chat(MESSAGES, timeout=10))
        self.assertEqual(client.cache, {})

    def test_retry_wait_cannot_cross_cutoff(self):
        client = self.client((500, {}, b""), budget=llm.Budget(planned_base_calls=5))
        self.clock.now = 1619
        self.fails("deadline", lambda: client.chat(MESSAGES))
        self.assertEqual(self.clock.waits, [])
        self.assertEqual(len(self.transport.calls), 1)

    def test_sleep_overshoot_rechecks_deadline(self):
        client = self.client((500, {}, b""), budget=llm.Budget(planned_base_calls=5))
        def oversleep(delay):
            self.clock.now = 1621
        client.sleep = oversleep
        self.fails("deadline", lambda: client.chat(MESSAGES))
        self.assertEqual(len(self.transport.calls), 1)

    def test_small_budget_exhaustion_before_dispatch(self):
        client = self.client(budget=llm.Budget(token_ceiling=1))
        self.fails("token_budget", lambda: client.chat(MESSAGES))
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(client.budget.records, [])

    def test_unknown_usage_blocks_later_reservation(self):
        client = self.client(response(usage=False), budget=llm.Budget(token_ceiling=400))
        client.chat(MESSAGES, max_tokens=100)
        self.fails("token_budget", lambda: client.chat(MESSAGES, max_tokens=101))
        self.assertEqual(len(self.transport.calls), 1)
        self.assertGreater(client.budget.summary()["unknown_usage_reservations"], 0)

    def test_reported_undercount_overage_stops_run(self):
        client = self.client(response(usage={"prompt_tokens": 5000, "completion_tokens": 1}),
                             budget=llm.Budget(token_ceiling=500))
        self.fails("token_budget", lambda: client.chat(MESSAGES, max_tokens=10))
        self.assertTrue(client.budget.summary()["over_ceiling"])
        self.assertEqual(client.cache, {})

    def test_reservation_exists_before_transport(self):
        budget = llm.Budget()
        def observe():
            self.assertGreater(budget.summary()["outstanding_reservations"], 0)
            self.assertEqual(budget.summary()["attempts"], 1)
            return response()
        client = self.client(observe, budget=budget)
        client.chat(MESSAGES)
        self.assertEqual(budget.summary()["outstanding_reservations"], 0)

    def test_concurrent_reservations_cannot_spend_same_balance(self):
        budget = llm.Budget(token_ceiling=100)
        barrier = threading.Barrier(3)
        outcomes = []
        def reserve():
            barrier.wait(timeout=2)
            try:
                budget.reserve(object(), 50, 50, 50)
                outcomes.append("reserved")
            except llm.LLMError as error:
                outcomes.append(error.detail["code"])
        workers = [threading.Thread(target=reserve) for _ in range(2)]
        for worker in workers:
            worker.start()
        barrier.wait(timeout=2)
        for worker in workers:
            worker.join(2)
            self.assertFalse(worker.is_alive())
        self.assertCountEqual(outcomes, ["reserved", "token_budget"])
        self.assertEqual(budget.summary()["charged_tokens"], 100)

    def test_cache_hit_sends_no_request_and_spends_no_tokens(self):
        client = self.client()
        first = client.chat(MESSAGES)
        before = client.budget.summary()
        self.assertEqual(client.chat(copy.deepcopy(MESSAGES)), first)
        self.assertEqual(client.budget.summary(), before)
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(client.cache_hits, 1)
        self.assertTrue(client.last_metadata["cached"])

    def test_cache_context_versions_and_fingerprints_invalidate(self):
        client = self.client(*[response()] * 9)
        context = {"stage": "synthetic", "schema_version": "1", "prompt_version": "1",
                   "model_version": "v1", "input_fingerprint": "one", "context_fingerprint": "one",
                   "timezone_policy": "unspecified", "as_of": 100}
        client.request(MESSAGES, cache_context=context)
        for name in context:
            changed = dict(context, **{name: "changed"})
            client.request(MESSAGES, cache_context=changed)
        self.assertEqual(len(self.transport.calls), 9)

    def test_cache_request_and_environment_changes_invalidate(self):
        client = self.client(*[response()] * 9)
        client.chat(MESSAGES)
        client.chat([{"role": "user", "content": "changed input"}])
        client.chat(MESSAGES, temperature=1)
        client.chat(MESSAGES, max_tokens=10)
        client.chat(MESSAGES, model="another-version")
        client.chat(MESSAGES, timeout=20)
        with patch.dict(os.environ, {"LLM_MODEL": "env-change"}):
            client.chat(MESSAGES)
        with patch.dict(os.environ, {"LLM_BASE_URL": "https://other.invalid/v1"}):
            client.chat(MESSAGES)
        with patch.dict(os.environ, {"LLM_API_KEY": "rotated-synthetic"}):
            client.chat(MESSAGES)
        self.assertEqual(len(self.transport.calls), 9)
        self.assertTrue(all(len(key) == 64 for key in client.cache))
        self.assertNotIn(ENV["LLM_API_KEY"], str(client.cache))

    def test_cache_client_context_mutation_invalidate(self):
        context = {"seed": {"revision": 1}}
        client = self.client(response(), response(), cache_context=context)
        client.chat(MESSAGES)
        context["seed"]["revision"] = 2
        client.chat(MESSAGES)
        self.assertEqual(len(self.transport.calls), 2)

    def test_failures_never_cached(self):
        client = self.client(response(""), response())
        self.fails("empty", lambda: client.chat(MESSAGES))
        self.assertEqual(client.chat(MESSAGES), "synthetic reply")
        self.assertEqual(len(self.transport.calls), 2)

    def test_cache_hit_revalidates_and_evicts_rejected_content(self):
        client = self.client()
        client.request(MESSAGES, validate=lambda text: True)
        self.fails("validation", lambda: client.request(MESSAGES, validate=lambda text: False))
        self.assertEqual(client.cache, {})

    def test_json_schema_without_caller_validation_not_cached(self):
        client = self.client(response('{"ok":true}'), response('{"ok":true}'))
        fmt = {"type": "json_schema", "json_schema": {"name": "synthetic", "schema": {"type": "object"}}}
        client.chat(MESSAGES, response_format=fmt)
        client.chat(MESSAGES, response_format=fmt)
        self.assertEqual(len(self.transport.calls), 2)
        self.assertEqual(client.cache, {})

    def test_cache_rejected_after_cutoff(self):
        client = self.client()
        client.chat(MESSAGES)
        self.clock.now = 1620
        self.fails("deadline", lambda: client.chat(MESSAGES))

    def test_private_values_never_in_diagnostics_or_disk_logs(self):
        private = "PRIVATE-PROMPT-RESPONSE"
        client = self.client(ValueError(ENV["LLM_API_KEY"] + private))
        with patch("builtins.open", side_effect=AssertionError("No log file expected")), \
                patch("sys.stdout", new_callable=io.StringIO) as out, \
                patch("sys.stderr", new_callable=io.StringIO) as err:
            error = self.fails("transport", lambda: client.chat([{"role": "user", "content": private}]))
        diagnostics = str(error) + repr(error.detail) + repr(client.budget.records) + out.getvalue() + err.getvalue()
        self.assertNotIn(private, diagnostics)
        self.assertNotIn(ENV["LLM_API_KEY"], diagnostics)

    def test_interruption_keeps_reservation_and_marks_failure(self):
        client = self.client(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            client.chat(MESSAGES)
        self.assertEqual(client.budget.records[0]["outcome"], "interrupted")
        self.assertTrue(client.budget.records[0]["unknown_usage"])
        self.assertEqual(client.cache, {})

    def test_cleanup_failure_prevents_new_workers(self):
        client = self.client(llm.LLMError("worker_cleanup", "Synthetic cleanup failure."))
        for _ in range(2):
            self.fails("worker_cleanup", lambda: client.chat(MESSAGES))
        self.assertEqual(len(self.transport.calls), 1)

    def test_python39_grammar(self):
        for path in (PROJECT / "llm.py", Path(__file__)):
            ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))

    def test_regression_preparation_cannot_dispatch_after_cutoff(self):
        client = self.client()
        estimate = client.budget.estimate
        def slow_estimate(body):
            self.clock.now = 1621
            return estimate(body)
        with patch.object(client.budget, "estimate", side_effect=slow_estimate):
            self.fails("deadline", lambda: client.chat(MESSAGES))
        self.assertEqual(self.transport.calls, [])

    def test_regression_unsupported_retry_delay_never_retries_early(self):
        for delay in ("Wed, 05 Nov 2031 10:00:00 GMT", "NaN", "inf", "invalid"):
            with self.subTest(delay=delay):
                client = self.client((429, {"Retry-After": delay}, b""),
                                     budget=llm.Budget(planned_base_calls=5))
                self.fails("retry_delay", lambda: client.chat(MESSAGES))
                self.assertEqual(len(self.transport.calls), 1)
                self.assertEqual(self.clock.waits, [])

    def test_regression_partial_usage_details_are_a_known_lower_bound(self):
        client = self.client(response(usage={"prompt_tokens": 12,
                             "completion_tokens_details": {"reasoning_tokens": 999}}))
        client.chat(MESSAGES, max_tokens=10)
        self.assertEqual(client.budget.records[0]["charged_tokens"], 1011)
        self.assertTrue(client.budget.records[0]["unknown_usage"])

    def test_regression_invalid_reservations_cannot_create_budget_credit(self):
        budget = llm.Budget(token_ceiling=100)
        for values in ((1, -5, 10), (1, 1, -5), (0, 1, 1), (True, 1, 1)):
            self.fails("configuration", lambda: budget.reserve(object(), *values))
        self.assertEqual(budget.records, [])

    def test_regression_reservation_rechecks_latest_calibration(self):
        budget = llm.Budget(token_ceiling=100)
        budget.safety_factor = 2
        self.fails("token_budget", lambda: budget.reserve(object(), 50, 50, 1))


class ProcessTests(unittest.TestCase):
    def test_real_spawn_success_and_reap(self):
        transport = llm.ProcessTransport(worker=success_worker)
        status, headers, body = transport("unused", b"{}", "synthetic", 5)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["choices"][0]["message"]["content"], "synthetic reply")
        self.assertEqual([event["event"] for event in transport.events], ["start", "reaped"])
        self.assertEqual(transport.events[-1]["exitcode"], 0)

    def test_real_hung_and_partial_transfer_workers_terminated(self):
        before = {p.pid for p in multiprocessing.active_children()}
        for worker in (hang_worker, partial_worker):
            with self.subTest(worker=worker.__name__):
                transport = llm.ProcessTransport(worker=worker)
                started = time.monotonic()
                with self.assertRaises(llm.LLMError) as caught:
                    transport("unused", b"{}", "synthetic", 1.2)
                elapsed = time.monotonic() - started
                self.assertEqual(caught.exception.detail["code"], "timeout")
                self.assertLess(elapsed, 3)
                self.assertEqual([event["event"] for event in transport.events], ["start", "terminate", "reaped"])
                self.assertNotEqual(transport.events[-1]["exitcode"], 0)
                self.assertEqual({p.pid for p in multiprocessing.active_children()}, before)

    def test_real_crash_and_empty_worker_fail_explicitly(self):
        for worker in (crash_worker, empty_worker):
            transport = llm.ProcessTransport(worker=worker)
            with self.assertRaises(llm.LLMError) as caught:
                transport("unused", b"{}", "synthetic", 5)
            self.assertEqual(caught.exception.detail["code"], "worker_failure")
            self.assertEqual(transport.events[-1]["event"], "reaped")

    def test_kill_escalation_and_bounded_joins_with_synthetic_process(self):
        # Windows TerminateProcess cannot be ignored like POSIX SIGTERM. Verify
        # escalation logic here; actual ignored-SIGTERM Linux test remains H1.
        class Process:
            pid = 123
            exitcode = None
            alive = True
            daemon = False
            def start(self): pass
            def join(self, timeout): waits.append(timeout)
            def is_alive(self): return self.alive
            def terminate(self): actions.append("terminate")
            def kill(self):
                actions.append("kill")
                self.alive = False
                self.exitcode = -9
            def close(self): actions.append("close")
        class Context:
            def RawArray(self, kind, size): return bytearray(size)
            def Process(self, **kwargs): return Process()
        waits, actions = [], []
        with patch.object(llm.multiprocessing, "get_context", return_value=Context()):
            with self.assertRaises(llm.LLMError):
                llm.ProcessTransport()("unused", b"{}", "synthetic", 1)
        self.assertEqual(actions, ["terminate", "kill", "close"])
        self.assertTrue(all(0 <= wait <= 1 for wait in waits))

    def test_http_worker_configured_endpoint_only_and_no_redirects(self):
        class Response(io.BytesIO):
            code = 200
            headers = {}
        class Opener:
            def open(self, request, timeout):
                requests.append(request)
                return Response(response()[2])
        buffer = bytearray(65536)
        requests = []
        with patch.object(llm.urllib.request, "build_opener", return_value=Opener()) as factory:
            llm._http_worker(buffer, "https://synthetic.invalid/chat/completions", b"{}", "synthetic",
                             time.monotonic() + 1, 1024)
        self.assertEqual(requests[0].full_url, "https://synthetic.invalid/chat/completions")
        self.assertEqual(requests[0].get_header("Authorization"), "Bearer synthetic")
        self.assertEqual(factory.call_args.args[0].proxies, {})
        self.assertIsInstance(factory.call_args.args[1], llm._NoRedirect)
        self.assertIsNone(llm._NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid"))
        length = struct.unpack("!Q", buffer[:8])[0]
        self.assertEqual(json.loads(buffer[8:8 + length])["status"], 200)

    def test_worker_response_limit_is_explicit_failure(self):
        class Response(io.BytesIO):
            code = 200
            headers = {}
        class Opener:
            def open(self, request, timeout): return Response(b"x" * 50)
        buffer = bytearray(65536)
        with patch.object(llm.urllib.request, "build_opener", return_value=Opener()):
            llm._http_worker(buffer, "https://synthetic.invalid/chat/completions", b"{}", "synthetic",
                             time.monotonic() + 1, 10)
        length = struct.unpack("!Q", buffer[:8])[0]
        self.assertEqual(json.loads(buffer[8:8 + length]), {"error": "response_too_large"})

    def test_regression_expired_worker_never_opens_endpoint(self):
        buffer = bytearray(65536)
        with patch.object(llm.urllib.request, "build_opener") as factory:
            llm._http_worker(buffer, "https://synthetic.invalid/chat/completions",
                             b"{}", "synthetic", 0, 1024)
        factory.assert_not_called()
        length = struct.unpack("!Q", buffer[:8])[0]
        self.assertEqual(json.loads(buffer[8:8 + length]), {"error": "deadline"})

    def test_regression_invalid_certificate_is_permanent(self):
        class Opener:
            def open(self, request, timeout):
                raise urllib.error.URLError(ssl.SSLCertVerificationError("synthetic invalid certificate"))
        buffer = bytearray(65536)
        with patch.object(llm.urllib.request, "build_opener", return_value=Opener()):
            llm._http_worker(buffer, "https://synthetic.invalid/chat/completions",
                             b"{}", "synthetic", time.monotonic() + 5, 1024)
        length = struct.unpack("!Q", buffer[:8])[0]
        self.assertEqual(json.loads(buffer[8:8 + length]), {"error": "configuration"})


if __name__ == "__main__":
    unittest.main()
