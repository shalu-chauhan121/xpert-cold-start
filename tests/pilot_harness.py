"""Session-04 test-only pilot safety harness (Gates 6-7 preparation).

Enforces the proposed pilot envelope INDEPENDENTLY of `llm.Budget` (defense in
depth; both layers must agree):

- global maximum 30 transmissions, retries included (25 planned base jobs
  + at most 5 recoveries);
- separate maximum 5 recovery attempts;
- 250,000-token reservation via the run Budget;
- proposed USD 2.00 ceiling computed with SEPARATE input/output token rates
  from a verified price table;
- network/finalize/overall deadlines (600/750/780 s) via `llm.Deadline`.

The envelope is a PLANNING CONSTRAINT, not spending authorization. A real pilot
additionally requires user-approved credentials, provider-side spend controls
and verified pricing; anything unknown fails closed before construction
(`fail_closed`). No credentials, endpoints or prices are hardcoded here.
"""
import math
import os
import time

from llm import Budget, Client, Deadline, LLMError


class PilotRefusal(RuntimeError):
    """Harness refuses to dispatch or stops a run; carries a machine code."""

    def __init__(self, code, message):
        self.code = code
        super().__init__(code + ": " + message)


class PilotLimits:
    """Proposed envelope; planning constraints, NOT spend authorization."""

    max_transmissions = 30          # every dispatch attempt, retries included
    max_recoveries = 5              # separate recovery allowance
    token_reservation = 250000
    spend_ceiling_usd = 2.00        # requires verified pricing before real use
    network_seconds = 600
    finalize_seconds = 750
    overall_seconds = 780

    @property
    def base_calls(self):
        """Planned original calls keep floor(base/5) transmissions for recovery."""
        return self.max_transmissions - self.max_recoveries

    @property
    def recovery_limit(self):
        return self.base_calls // 5

    def validate(self):
        limits = (self.max_transmissions, self.max_recoveries,
                  self.token_reservation, self.spend_ceiling_usd,
                  self.network_seconds, self.finalize_seconds, self.overall_seconds)
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0
               for v in limits):
            raise PilotRefusal("configuration", "Pilot limits must be positive numbers.")
        if not 0 < self.network_seconds < self.finalize_seconds < self.overall_seconds:
            raise PilotRefusal("configuration", "Deadline ordering is invalid.")
        if self.recovery_limit > self.max_recoveries:
            raise PilotRefusal("configuration", "Recovery allowance exceeds recovery cap.")
        if self.base_calls + self.max_recoveries != self.max_transmissions:
            raise PilotRefusal("configuration", "Envelope does not add up.")
        return True


_PRICE_KEYS = ("input_usd_per_mtok", "output_usd_per_mtok")


def normalize_pricing(table):
    """Verified price table: separate input/output rates, USD, documented source.

    Unknown, malformed or nonnumeric pricing fails closed; booleans do not
    count as numbers; negative or nonfinite rates are refused.
    """
    required = ("model", "source", "currency") + _PRICE_KEYS
    if not isinstance(table, dict) or not set(table) >= set(required):
        raise PilotRefusal("fail_closed", "Verified pricing is missing required fields: " + ", ".join(required))
    if table["currency"] != "USD":
        raise PilotRefusal("fail_closed", "Pricing must be documented in USD.")
    for key in ("model", "source"):
        value = table[key]
        if not isinstance(value, str) or not value.strip():
            raise PilotRefusal("fail_closed", "Verified pricing needs " + key + " documentation.")
    rates = {}
    for key in _PRICE_KEYS:
        value = table[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise PilotRefusal("fail_closed", "Verified " + key + " must be a number, got: "
                               + type(value).__name__ + ".")
        if not math.isfinite(value) or value < 0:
            raise PilotRefusal("fail_closed", "Verified " + key + " must be finite and nonnegative.")
        rates[key] = float(value)
    return {"model": table["model"], "source": table["source"], "currency": "USD", **rates}


def project_cost(input_usd_per_mtok, output_usd_per_mtok, prompt_tokens, completion_tokens):
    """Separate-rate projection: input tokens price at the input rate only."""
    return (input_usd_per_mtok * prompt_tokens +
            output_usd_per_mtok * completion_tokens) / 1e6


REQUIRED_ENVIRONMENT = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")


class PilotHarness:
    """Owns one Client/Budget/Deadline for the bounded pilot run.

    mode == "test" exactly when an inline transport is injected (offline).
    Real mode refuses construction unless pricing is verified, provider-side
    spend controls are confirmed and all required environment values exist.
    """

    def __init__(self, transport=None, clock=time.monotonic, sleep=time.sleep,
                 verified_pricing=None, provider_controls_confirmed=False,
                 capture=None, capture_max_bytes=4096):
        self.limits = PilotLimits()
        self.limits.validate()
        self.mode = "test" if transport is not None else "real"
        self.clock, self.sleep = clock, sleep
        self.pricing = None
        if verified_pricing is not None:
            self.pricing = normalize_pricing(verified_pricing)
        if self.mode == "real":
            if self.pricing is None:
                raise PilotRefusal("fail_closed",
                                   "Real dispatch requires verified pricing before start.")
            if not provider_controls_confirmed:
                raise PilotRefusal("fail_closed",
                                   "Real dispatch requires confirmed provider-side spend controls.")
            if any(not os.environ.get(name, "").strip() for name in REQUIRED_ENVIRONMENT):
                raise PilotRefusal("fail_closed",
                                   "Real dispatch requires the run endpoint, key and model.")
        self.stopped = None
        self.budget = Budget(self.limits.token_reservation, self.limits.base_calls)
        self.deadline = Deadline(clock=clock, network=self.limits.network_seconds,
                                 exit_target=self.limits.finalize_seconds,
                                 overall=self.limits.overall_seconds)
        self.client = Client(transport=transport, clock=clock, sleep=sleep,
                             budget=self.budget, deadline=self.deadline,
                             capture=capture, capture_max_bytes=capture_max_bytes)

    def stop(self, reason):
        if self.stopped is None:
            self.stopped = reason

    def _assert_caps(self, summary):
        if summary["attempts"] > self.limits.max_transmissions:
            self.stop("transmission_cap")
            return False
        if summary["recoveries"] > self.limits.max_recoveries:
            self.stop("recovery_cap")
            return False
        return True

    def projected_usd(self):
        if self.pricing is None:
            return None
        summary = self.budget.summary()
        prompt = max(summary["estimated_prompt_tokens"], summary["reported_prompt_tokens"])
        completion = max(summary["reserved_completion_tokens"],
                         summary["reported_completion_tokens"])
        return project_cost(self.pricing["input_usd_per_mtok"],
                            self.pricing["output_usd_per_mtok"], prompt, completion)

    def _preflight(self, **kwargs):
        if self.stopped is not None:
            raise PilotRefusal("stopped", "Run stopped: " + self.stopped)
        summary = self.budget.summary()
        if summary["attempts"] >= self.limits.max_transmissions:
            raise PilotRefusal("transmission_cap",
                               "Global transmission cap reached; no further dispatch.")
        job = kwargs.get("job_id")
        retried = job is not None and self.budget.jobs.get(job, 0) > 0
        if retried and summary["recoveries"] >= self.limits.max_recoveries:
            raise PilotRefusal("recovery_cap", "Recovery cap reached; no further retry.")
        try:
            self.deadline.check()
        except LLMError:
            self.stop("deadline_exhausted")
            raise PilotRefusal("deadline_exhausted",
                               "Network allowance exhausted; stop dispatch and finalize.")
        if self.pricing is not None:
            projected = self.projected_usd()
            if projected > self.limits.spend_ceiling_usd:
                self.stop("spend_ceiling")
                raise PilotRefusal("spend_ceiling",
                                   "Projected spend %.6f USD exceeds the %.2f USD ceiling."
                                   % (projected, self.limits.spend_ceiling_usd))

    def _postflight(self):
        summary = self.budget.summary()
        if not self._assert_caps(summary) or summary["over_ceiling"]:
            if summary["over_ceiling"]:
                self.stop("token_ceiling")
            return
        records = self.budget.records
        last = records[-1] if records else None
        if last is not None and last["outcome"] == "success" and last["unknown_usage"]:
            self.stop("unknown_usage")

    def request(self, **kwargs):
        """One supervised dispatch; preflight and postflight bracket the client."""
        self._preflight(**kwargs)
        try:
            content = self.client.request(**kwargs)
        finally:
            self._postflight()
        return content
