"""Run-local Chat Completions client; the only runtime network boundary.

chat() still returns text. Failures raise LLMError with a safe structured detail.
Configure one Client/Budget per run; request() adds job/context/validation seams
for later stages without implementing them. No raw request/response disk logs in
this module; an OPTIONAL capture callback records bounded response-side
telemetry (structured response bodies, job identifiers, finish reasons, HTTP
status, safety-filter and validation outcomes) for pilot evidence. Requests,
wire bodies, transport headers and credentials are never visible to it.
The default completion allowance (1024) is a request cap, NOT a model limit.
Unknown context limits and dollar prices are deliberately not guessed.
"""
import base64
import hashlib
import io
import json
import math
import multiprocessing
import os
import ssl
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# read_json is the shared strict JSON reader (with Session-08 tolerant
# recovery of fences/prose around one balanced object). validation.py is
# stdlib-only, so this edge is acyclic and keeps ONE parse policy.
from validation import read_json


_RUN_START = time.monotonic()


class LLMError(RuntimeError):
    """Only locally defined diagnostics; never interpolate provider exceptions."""

    def __init__(self, code, message, retryable=False, split_recommended=False,
                 status=None):
        self.detail = {"code": code, "message": message, "retryable": retryable,
                       "split_recommended": split_recommended, "status": status}
        super().__init__(code + ": " + message)


def _positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _integer(value):
    return type(value) is int and value >= 0


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError("Duplicate key")
            result[key] = item
        return result

    def constant(_):
        raise ValueError("Nonfinite JSON")

    return json.loads(value, object_pairs_hook=pairs, parse_constant=constant)


class Deadline:
    def __init__(self, clock=time.monotonic, started=None, network=1620,
                 exit_target=1770, overall=1800):
        if not 0 < network < exit_target < overall:
            raise LLMError("configuration", "Deadline ordering is invalid.")
        self.clock = clock
        self.started = clock() if started is None else started
        self.network = network
        self.exit_target = exit_target
        self.overall = overall

    def elapsed(self):
        return max(0, self.clock() - self.started)

    def network_remaining(self):
        return self.network - self.elapsed()

    def check(self, finalizing=False):
        limit = self.exit_target if finalizing else self.network
        if self.elapsed() >= limit:
            raise LLMError("exit_deadline" if finalizing else "deadline",
                           "Time allowance exhausted; stop dispatch and finalize the run.")


class Budget:
    """Atomic reservations shared by all clients/jobs in a run.

    A declared plan authorizes floor(base calls / 5) shared extra transmissions.
    Without a declared plan, original calls are allowed but recovery is disabled.
    Reuse the SAME job_id for later repair/split children. No splitting here.
    Usage detail categories are subsets, not added again to provider totals.
    """

    def __init__(self, token_ceiling=None, planned_base_calls=None):
        if token_ceiling is not None and not _integer(token_ceiling):
            raise LLMError("configuration", "Token ceiling must be a nonnegative integer.")
        if planned_base_calls is not None and not _integer(planned_base_calls):
            raise LLMError("configuration", "Planned calls must be a nonnegative integer.")
        self.token_ceiling = token_ceiling
        self.planned_base_calls = planned_base_calls
        self.recovery_limit = (planned_base_calls or 0) // 5
        self.recoveries = 0
        self.jobs = {}
        self.records = []
        self.lock = threading.RLock()
        self.safety_factor = 1.0
        self.estimator = "conservative UTF-8 bytes + framing proxy (not a guaranteed bound)"

    def estimate(self, body):
        # Entire wire body includes schemas/settings/instructions/context. Byte
        # counting avoids a four-characters-per-token assumption for mixed scripts.
        with self.lock:
            raw = len(body) + 32
            return raw, math.ceil(raw * self.safety_factor)

    def _charged(self):
        return sum(r["charged_tokens"] for r in self.records)

    def reserve(self, job_id, raw_prompt, prompt, completion):
        with self.lock:
            if any(not _integer(n) or n < 1 for n in (raw_prompt, prompt, completion)):
                raise LLMError("configuration", "Reservations require positive integer token allowances.")
            # Another client may have calibrated between estimate() and reserve().
            prompt = max(prompt, math.ceil(raw_prompt * self.safety_factor))
            attempts = self.jobs.get(job_id, 0)
            if attempts >= 3:
                raise LLMError("attempt_limit", "Original job has used all three transmissions.")
            if attempts and self.recoveries >= self.recovery_limit:
                raise LLMError("recovery_budget", "Shared 20% recovery allowance is exhausted.")
            if (not attempts and self.planned_base_calls is not None and
                    len(self.jobs) >= self.planned_base_calls):
                raise LLMError("call_budget", "Declared base-job allowance is exhausted.")
            if (self.token_ceiling is not None and
                    self._charged() + prompt + completion > self.token_ceiling):
                raise LLMError("token_budget", "Insufficient tokens for a conservative reservation.")
            self.jobs[job_id] = attempts + 1
            self.recoveries += int(attempts > 0)
            record = {"attempt": attempts + 1, "recovery": bool(attempts), "retry": False,
                      "raw_prompt_estimate": raw_prompt, "estimated_prompt_tokens": prompt,
                      "reserved_completion_tokens": completion,
                      "charged_tokens": prompt + completion, "outstanding": True,
                      "unknown_usage": True, "reported_prompt_tokens": None,
                      "reported_completion_tokens": None, "reported_total_tokens": None,
                      "additional_usage": {}, "elapsed": 0.0, "wait": 0.0,
                      "outcome": "in_flight"}
            self.records.append(record)
            return record

    def settle(self, record, usage, outcome, elapsed, status=None):
        with self.lock:
            usage = usage if isinstance(usage, dict) else {}
            p, c, total = (usage.get(k) for k in
                           ("prompt_tokens", "completion_tokens", "total_tokens"))
            p, c, total = (n if _integer(n) else None for n in (p, c, total))
            record.update(outstanding=False, outcome=outcome, elapsed=elapsed,
                          http_status=status if _integer(status) else None,
                          reported_prompt_tokens=p, reported_completion_tokens=c,
                          reported_total_tokens=total, unknown_usage=p is None or c is None)
            # Only numeric known category names are diagnostics; no arbitrary
            # provider strings, text, identifiers or error bodies enter the ledger.
            lower_bounds = {}
            for group in ("prompt_tokens_details", "completion_tokens_details"):
                details = usage.get(group)
                lower_bounds[group] = 0
                if isinstance(details, dict):
                    for name in ("cached_tokens", "audio_tokens", "reasoning_tokens",
                                 "accepted_prediction_tokens", "rejected_prediction_tokens"):
                        if _integer(details.get(name)):
                            record["additional_usage"][group + "." + name] = details[name]
                            # Categories may overlap. The largest is a known
                            # lower bound even when its containing total is absent.
                            lower_bounds[group] = max(lower_bounds[group], details[name])
            accounted = (max(p if p is not None else record["estimated_prompt_tokens"],
                             lower_bounds["prompt_tokens_details"]) +
                         max(c if c is not None else record["reserved_completion_tokens"],
                             lower_bounds["completion_tokens_details"]))
            # Total may include additional billed categories. Detail subsets must
            # not be summed twice. Inconsistent totals never reduce the charge.
            record["charged_tokens"] = max(accounted, total or 0)
            if p is not None and p > record["estimated_prompt_tokens"]:
                self.safety_factor = max(self.safety_factor,
                                         1.1 * p / record["raw_prompt_estimate"])

    def summary(self):
        with self.lock:
            details = {}
            for record in self.records:
                for name, count in record["additional_usage"].items():
                    details[name] = details.get(name, 0) + count
            return {"attempts": len(self.records), "recoveries": self.recoveries,
                    "retries": sum(r["retry"] for r in self.records),
                    "recovery_limit": self.recovery_limit,
                    "charged_tokens": self._charged(),
                    "outstanding_reservations": sum(r["charged_tokens"] for r in self.records
                                                    if r["outstanding"]),
                    "unknown_usage_reservations": sum(r["charged_tokens"] for r in self.records
                                                      if r["unknown_usage"] and not r["outstanding"]),
                    "estimated_prompt_tokens": sum(r["estimated_prompt_tokens"] for r in self.records),
                    "reserved_completion_tokens": sum(r["reserved_completion_tokens"] for r in self.records),
                    "reported_prompt_tokens": sum(r["reported_prompt_tokens"] or 0 for r in self.records),
                    "reported_completion_tokens": sum(r["reported_completion_tokens"] or 0 for r in self.records),
                    "reported_total_tokens": sum(r["reported_total_tokens"] or 0 for r in self.records),
                    "additional_usage": details,
                    "unknown_usage_attempts": sum(r["unknown_usage"] for r in self.records),
                    "elapsed": sum(r["elapsed"] for r in self.records),
                    "wait": sum(r["wait"] for r in self.records),
                    "estimator": self.estimator, "safety_factor": self.safety_factor,
                    "over_ceiling": self.token_ceiling is not None and self._charged() > self.token_ceiling,
                    "dollar_cost": None}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Credentials and requests never follow another endpoint.


def _write_worker_result(buffer, value):
    encoded = _json(value)
    if len(encoded) > len(buffer) - 8:
        encoded = _json({"error": "response_too_large"})
    buffer[8:8 + len(encoded)] = encoded
    buffer[:8] = struct.pack("!Q", len(encoded))


def _http_worker(buffer, endpoint, body, key, deadline, max_bytes):
    """No child subprocesses, detached workers, pipes, or queue feeder threads."""
    try:
        if time.monotonic() >= deadline:
            _write_worker_result(buffer, {"error": "deadline"})
            return
        request = urllib.request.Request(endpoint, data=body, headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json"})
        # Disable environment proxy routing as well as redirects.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        timeout = deadline - time.monotonic()
        if timeout <= 0:
            _write_worker_result(buffer, {"error": "deadline"})
            return
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            status = response.code
            delay = response.headers.get("Retry-After", "")
            # Never retain HTTP error bodies, which can echo private input.
            raw = response.read(max_bytes + 1) if 200 <= status < 300 else b""
        if len(raw) > max_bytes:
            result = {"error": "response_too_large"}
        else:
            result = {"status": status, "retry_after": delay,
                      "body": base64.b64encode(raw).decode("ascii")}
    except ssl.SSLCertVerificationError:
        result = {"error": "configuration"}
    except urllib.error.URLError as error:
        result = {"error": "configuration" if isinstance(error.reason, ssl.SSLCertVerificationError)
                  else "network"}
    except (TimeoutError, OSError):
        result = {"error": "network"}
    except BaseException:
        result = {"error": "worker_failure"}
    _write_worker_result(buffer, result)


class ProcessTransport:
    """Spawn on Windows/Linux. Read shared bytes only AFTER bounded child exit.

    A partial IPC transfer cannot block the parent in recv(). Timeout includes
    cleanup grace; start() itself depends on the OS. A hung parent still requires
    the future launcher supervisor. Injected direct transports are test-only.
    """

    def __init__(self, worker=_http_worker, grace=0.2, max_bytes=2 * 1024 * 1024):
        if not _positive(grace) or not _integer(max_bytes) or max_bytes < 1:
            raise LLMError("configuration", "Worker grace and response size limit must be positive.")
        self.worker = worker
        self.grace = grace
        self.max_bytes = max_bytes
        self.events = []

    def __call__(self, endpoint, body, key, timeout):
        end = time.monotonic() + timeout
        if not _positive(timeout) or timeout <= 2 * self.grace:
            raise LLMError("deadline", "Insufficient time for worker cleanup.")
        context = multiprocessing.get_context("spawn")
        buffer = context.RawArray("B", (self.max_bytes * 4 // 3) + 8192)
        process = context.Process(target=self.worker, args=(buffer, endpoint, body, key,
                                                          end - 2 * self.grace, self.max_bytes))
        process.daemon = True
        launched = False
        try:
            if time.monotonic() >= end - 2 * self.grace:
                raise LLMError("deadline", "Worker setup consumed the dispatch allowance.")
            process.start()
            launched = True
            self.events.append({"event": "start", "pid": process.pid, "at": time.monotonic()})
            process.join(max(0, end - time.monotonic() - 2 * self.grace))
            if process.is_alive():
                raise LLMError("timeout", "Request deadline reached; remote billing is unknown.", True)
            if process.exitcode != 0:
                raise LLMError("worker_failure", "Request worker exited without a result.", True)
            length = struct.unpack("!Q", bytes(buffer[:8]))[0]
            if not 0 < length <= len(buffer) - 8:
                raise LLMError("worker_failure", "Request worker returned incomplete IPC data.", True)
            result = _strict_json(bytes(buffer[8:8 + length]))
            if "error" in result:
                code = result["error"]
                raise LLMError(code, "Request worker could not return a complete response.",
                               code in ("network", "worker_failure"))
            return result["status"], {"Retry-After": result["retry_after"]}, base64.b64decode(result["body"])
        except LLMError:
            raise
        except Exception:
            raise LLMError("worker_failure", "Could not start or read the request worker.") from None
        finally:
            if launched:
                if process.is_alive():
                    self.events.append({"event": "terminate", "pid": process.pid, "at": time.monotonic()})
                    try:
                        process.terminate()
                    except OSError:
                        pass  # Race with exit; still join and escalate if alive.
                    process.join(self.grace)
                if process.is_alive():
                    self.events.append({"event": "kill", "pid": process.pid, "at": time.monotonic()})
                    try:
                        process.kill()
                    except OSError:
                        pass
                    process.join(self.grace)
                if process.is_alive():
                    # Fatal: caller must stop, never dispatch another worker.
                    raise LLMError("worker_cleanup", "Operating system did not reap the terminated worker.")
                self.events.append({"event": "reaped", "pid": process.pid,
                                    "at": time.monotonic(), "exitcode": process.exitcode})
            process.close()


class Client:
    def __init__(self, transport=None, clock=time.monotonic, sleep=time.sleep,
                 budget=None, deadline=None, default_completion_tokens=1024,
                 cache_context=None, capture=None, capture_max_bytes=4096):
        if not _integer(default_completion_tokens) or default_completion_tokens < 1:
            raise LLMError("configuration", "Default completion allowance must be positive.")
        # Opt-in capture: a one-argument callable receiving bounded response-
        # side records. Default None keeps the disks-log-free behavior.
        if not _integer(capture_max_bytes) or capture_max_bytes < 1:
            raise LLMError("configuration", "Capture size cap must be a positive integer.")
        self.capture = capture
        self.capture_max_bytes = capture_max_bytes
        self.capture_failures = 0
        self.transport = transport if transport is not None else ProcessTransport()
        self.clock, self.sleep = clock, sleep
        self.deadline = deadline or Deadline(clock)
        self.budget = budget if budget is not None else Budget()
        self.default_completion_tokens = default_completion_tokens
        self.cache_context = cache_context or {}
        self.cache = {}
        self.cache_hits = 0
        self.last_metadata = None
        self.lock = threading.RLock()  # Serial dispatch; Budget lock also protects shared clients.
        self._credential = None
        self._fatal = False

    def _configuration(self, model):
        base, key, configured_model = (os.environ.get(n, "") for n in
                                       ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))
        if not all(v.strip() for v in (base, key, configured_model)):
            raise LLMError("configuration", "Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL.")
        try:
            parsed = urllib.parse.urlsplit(base)
            valid = (parsed.scheme in ("http", "https") and parsed.hostname and
                     not parsed.username and not parsed.password and not parsed.query and
                     not parsed.fragment and parsed.port != 0 and
                     not any(c.isspace() or ord(c) < 32 for c in base))
        except ValueError:
            valid = False
        if not valid or any(ord(c) < 32 or ord(c) > 126 for c in key):
            raise LLMError("configuration", "Endpoint or credential format is invalid.")
        chosen = configured_model if model is None else model
        if not isinstance(chosen, str) or not chosen.strip():
            raise LLMError("configuration", "Model must be a nonempty string.")
        # Key never enters cache keys. Credential rotation invalidates in memory.
        if self._credential != key:
            self.cache.clear()
            self._credential = key
        return base.rstrip("/") + "/chat/completions", key, chosen

    def chat(self, messages, model=None, temperature=None, max_tokens=None,
             response_format=None, timeout=120):
        return self.request(messages, model, temperature, max_tokens, response_format, timeout)

    def request(self, messages, model=None, temperature=None, max_tokens=None,
                response_format=None, timeout=120, *, job_id=None,
                cache_context=None, validate=None):
        """validate(text) must return normally only for complete stage results.

        Supply stage/schema/prompt/model versions, input/context fingerprints and
        timezone/as_of policy in cache_context. Mutable context is hashed afresh.
        Cache hits are revalidated, so validator changes cannot bypass checks.
        Stage semantics and missing-item repair belong to future reasoning.py.
        temperature=None (the default) is model-specific: omitted from the wire
        body for Gemini 3+ models, whose deprecated parameter is ignored by the
        provider, and 0 for every other model, preserving the pre-pilot default.
        Explicit finite numbers are sent unchanged for every provider.
        """
        with self.lock:
            self.last_metadata = None
            if self._fatal:
                raise LLMError("worker_cleanup", "Client stopped after a worker cleanup failure.")
            self.deadline.check()
            endpoint, key, chosen = self._configuration(model)
            cap = self.default_completion_tokens if max_tokens is None else max_tokens
            if (not _integer(cap) or cap < 1 or not _positive(timeout) or
                    temperature is not None and
                    (type(temperature) not in (int, float) or not math.isfinite(temperature)) or
                    not isinstance(messages, list) or not messages or
                    any(not isinstance(m, dict) or not isinstance(m.get("role"), str)
                        or "content" not in m for m in messages) or
                    (response_format is not None and not isinstance(response_format, dict))):
                raise LLMError("configuration", "Invalid chat messages or generation settings.")
            body = {"model": chosen, "messages": messages, "max_tokens": cap}
            resolved = temperature
            if resolved is None and not chosen.lower().startswith("gemini-3"):
                resolved = 0  # Non-Gemini-3 providers keep the prior default.
            if resolved is not None:
                body["temperature"] = resolved
            if response_format is not None:
                body["response_format"] = response_format
            try:
                wire = _json(body)
                cache_key = hashlib.sha256(_json({
                    "client_version": 1, "endpoint": endpoint, "request": body,
                    "context": self.cache_context, "request_context": cache_context,
                    "timeout": timeout})).hexdigest()
            except (ValueError, TypeError, UnicodeError, RecursionError):
                raise LLMError("configuration", "Request and cache context must be finite JSON.") from None
            cached = self.cache.get(cache_key)
            if cached is not None:
                try:
                    self._validate(cached[0], response_format, validate)
                    self.deadline.check()
                except LLMError:
                    del self.cache[cache_key]
                    raise
                self.cache_hits += 1
                self.last_metadata = dict(cached[1], cached=True)
                return cached[0]
            # An opaque object is a unique original identity without storing user text.
            job = object() if job_id is None else job_id
            previous_error = None
            while True:
                self.deadline.check()
                remaining = min(timeout, self.deadline.network_remaining())
                if remaining <= 0.5:
                    raise LLMError("deadline", "Insufficient time to dispatch and reap a worker.")
                raw, estimate = self.budget.estimate(wire)
                try:
                    record = self.budget.reserve(job, raw, estimate, cap)
                except LLMError as error:
                    if previous_error is not None:
                        error.detail["last_failure"] = previous_error.detail["code"]
                    raise
                started, usage, error = self.clock(), None, None
                record["retry"] = previous_error is not None
                payload = data = content = None
                try:
                    self.deadline.check()
                    remaining = min(timeout, self.deadline.network_remaining())
                    if remaining <= 0.5:
                        raise LLMError("deadline", "Preparation consumed the dispatch allowance.")
                    status, headers, response = self.transport(endpoint, wire, key, remaining)
                    # Response side only; `wire`/`headers`/`key` never enter
                    # any capture below. Responses byte-capped at capture.
                    payload = response
                    self.deadline.check()
                    if self.clock() - started > remaining:
                        raise LLMError("timeout", "Response arrived after its deadline; billing is unknown.", True)
                    if not 200 <= status < 300:
                        transient = status in (408, 429) or 500 <= status < 600
                        raise LLMError("authentication" if status in (401, 403) else "http_error",
                                       "Check credentials/configuration." if not transient else "Temporary HTTP failure.",
                                       transient, status=status)
                    try:
                        data = _strict_json(response)
                    except (ValueError, TypeError, UnicodeError, RecursionError):
                        raise LLMError("malformed", "Response is not valid JSON; repair requires a caller decision.") from None
                    usage = data.get("usage") if isinstance(data, dict) else None
                    content = self._content(data)
                    self._validate(content, response_format, validate)
                    self.deadline.check()
                    metadata = {"cached": False, "finish_reason": "stop",
                                "model": data.get("model"),
                                "system_fingerprint": data.get("system_fingerprint")}
                except LLMError as failure:
                    error = failure
                except (TimeoutError, OSError, urllib.error.URLError):
                    error = LLMError("network", "Transport failed; remote billing is unknown.", True)
                except Exception:
                    error = LLMError("transport", "Transport returned an invalid result.")
                except BaseException:
                    error = LLMError("interrupted", "Request interrupted; remote billing is unknown.")
                    raise
                finally:
                    self.budget.settle(record, usage,
                                       error.detail["code"] if error else "success",
                                       max(0, self.clock() - started),
                                       error.detail["status"] if error else None)
                    if self.capture is not None:
                        self._capture(record, payload, data, content, error,
                                      job_id, cache_context)
                if error is None:
                    # A finite proxy cannot undo an observed overage. Stop instead
                    # of claiming budget compliance; all reported usage is retained.
                    if self.budget.summary()["over_ceiling"]:
                        raise LLMError("token_budget", "Reported usage exceeded the token ceiling; stop the run.")
                    self.last_metadata = metadata
                    # Arbitrary provider JSON Schema needs the future caller's
                    # contract validator; parsing alone cannot justify caching.
                    if (not response_format or response_format.get("type") != "json_schema"
                            or validate is not None):
                        self.cache[cache_key] = (content, metadata)
                    return content
                if error.detail["code"] == "worker_cleanup":
                    self._fatal = True
                if not error.detail["retryable"]:
                    raise error
                with self.budget.lock:
                    eligible = (self.budget.jobs[job] < 3 and
                                self.budget.recoveries < self.budget.recovery_limit)
                if not eligible:
                    error.detail["recovery_exhausted"] = True
                    raise error
                delay = min(8.0, 2.0 ** (record["attempt"] - 1))
                if error.detail["status"] is not None:
                    try:
                        supplied = float(headers.get("Retry-After", "0") or "0")
                    except (ValueError, TypeError, AttributeError):
                        # HTTP-date delays require a trustworthy server/wall-clock
                        # mapping. Stop rather than silently retrying too early.
                        raise LLMError("retry_delay", "Retry-After is not a supported numeric delay; defer recovery.") from None
                    if not math.isfinite(supplied) or supplied < 0:
                        raise LLMError("retry_delay", "Retry-After is not a finite nonnegative delay.")
                    if supplied > delay:
                        if supplied > 8:
                            raise LLMError("retry_delay", "Provider retry delay exceeds the bounded wait policy.")
                        delay = supplied
                if delay + 0.5 >= self.deadline.network_remaining():
                    raise LLMError("deadline", "Retry wait would consume the network allowance.")
                wait_started = self.clock()
                self.sleep(delay)
                record["wait"] += max(0, self.clock() - wait_started)
                previous_error = error

    @staticmethod
    def _content(data):
        if not isinstance(data, dict):
            raise LLMError("malformed", "Expected a response object.")
        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise LLMError("incomplete", "Expected exactly one complete choice.")
        choice = choices[0]
        message = choice.get("message")
        if choice.get("finish_reason") == "length":
            raise LLMError("truncated", "Discarded truncated output; split the original job if authorized.",
                           split_recommended=True)
        if (choice.get("finish_reason") == "content_filter" or
                isinstance(message, dict) and message.get("refusal")):
            raise LLMError("refused", "Provider refused the request; review its scope.")
        if choice.get("finish_reason") != "stop" or not isinstance(message, dict):
            raise LLMError("incomplete", "Response lacks a complete text finish indicator.")
        if message.get("tool_calls") or message.get("function_call"):
            raise LLMError("incomplete", "Unexpected tool request is not a completed text result.")
        content = message.get("content")
        if not isinstance(content, str):
            raise LLMError("incomplete", "Response text is missing or has the wrong type.")
        if not content.strip():
            raise LLMError("empty", "Provider returned empty content.")
        return content

    @staticmethod
    def _validate(content, response_format, validate):
        if response_format and response_format.get("type") in ("json_object", "json_schema"):
            try:
                parsed = read_json(io.StringIO(content))
            except (ValueError, TypeError, UnicodeError, RecursionError):
                raise LLMError("malformed_content", "Content does not satisfy the requested JSON format.") from None
            if (response_format.get("type") == "json_object" and
                    not isinstance(parsed, dict)):
                raise LLMError("malformed_content", "Content does not satisfy the requested JSON format.") from None
        if validate is not None:
            try:
                result = validate(content)
                if result is False:
                    raise ValueError("Rejected")
            except Exception as error:
                # Only the local class name is retained; response text and
                # provider error bodies are never copied into diagnostics.
                raise LLMError("validation",
                               "Response failed caller validation ("
                               + type(error).__name__
                               + "); required fields or coverage may be missing.") from None

    # Only these caller-supplied local identifiers may enter captures; every
    # other cache-context value (texts, lists, anything) is dropped.
    _CAPTURE_CONTEXT_KEYS = ("stage", "prompt_version", "schema_version",
                             "context_fingerprint", "input_fingerprint",
                             "timezone_policy", "as_of")

    def _capture(self, record, payload, data, content, error, job_id, context):
        """One bounded response-side capture record per settled attempt.

        Never captures: the request/wire body, transport headers, endpoint,
        credentials, or provider error pages for non-2xx responses
        (unstructured bodies could echo request state). Bodies are byte-
        capped at capture_max_bytes with the full byte length and SHA-256
        retained so truncation is the only observable loss.
        """
        if self.capture is None:
            return
        try:
            done, model = None, None
            if isinstance(data, dict):
                choices = data.get("choices")
                if (isinstance(choices, list) and choices and
                        isinstance(choices[0], dict)):
                    reason = choices[0].get("finish_reason")
                    if isinstance(reason, str):
                        done = reason
                if isinstance(data.get("model"), str):
                    model = data["model"]
            # Provider error pages for non-2xx are never captured.
            skip_body = (error is not None and
                         _integer(error.detail.get("status")))
            body_bytes = body_sha = body_text = None
            body_truncated = False
            if not skip_body and isinstance(payload, (bytes, bytearray)):
                payload = bytes(payload)
                body_bytes = len(payload)
                body_sha = hashlib.sha256(payload).hexdigest()
                cut = payload[:self.capture_max_bytes]
                body_truncated = body_bytes > self.capture_max_bytes
                body_text = cut.decode("utf-8", errors="replace")
            content_text, content_truncated = None, False
            if isinstance(content, str) and content:
                encoded = content.encode("utf-8")
                content_truncated = len(encoded) > self.capture_max_bytes
                content_text = (encoded[:self.capture_max_bytes]
                                .decode("utf-8", errors="replace"))
            fields = {}
            if isinstance(context, dict):
                for name in self._CAPTURE_CONTEXT_KEYS:
                    value = context.get(name)
                    if isinstance(value, str) and len(value) <= 128:
                        fields[name] = value
                    elif (isinstance(value, (int, float)) and
                            not isinstance(value, bool) and
                            math.isfinite(value)):
                        fields[name] = value
            document = {
                "job_id": job_id if isinstance(job_id, str) else None,
                "context": fields,
                "attempt": record["attempt"], "recovery": record["recovery"],
                "retry": record["retry"], "outcome": record["outcome"],
                "http_status": (error.detail.get("status")
                                if isinstance(error, LLMError) else None),
                "finish_reason": done,
                "model": model,
                "error_detail": (error.detail.get("message")
                                 if isinstance(error, LLMError) else None),
                "body_bytes": body_bytes, "body_sha256": body_sha,
                "body_truncated": body_truncated, "body_text": body_text,
                "content_text": content_text,
                "content_truncated": content_truncated,
            }
            self.capture(document)
        except Exception:
            self.capture_failures += 1


_default_client = None
_default_lock = threading.Lock()


def chat(messages, model=None, temperature=None, max_tokens=None, response_format=None, timeout=120):
    """Compatibility wrapper; configure _default_client or use Client for a run."""
    global _default_client
    with _default_lock:
        if _default_client is None:
            ceiling = os.environ.get("LLM_TOKEN_CEILING")
            planned = os.environ.get("LLM_PLANNED_BASE_CALLS")
            try:
                budget = Budget(None if ceiling is None else int(ceiling),
                                None if planned is None else int(planned))
            except ValueError:
                raise LLMError("configuration", "Token ceiling and planned calls must be integers.") from None
            _default_client = Client(budget=budget, deadline=Deadline(started=_RUN_START))
    return _default_client.chat(messages, model, temperature, max_tokens, response_format, timeout)
