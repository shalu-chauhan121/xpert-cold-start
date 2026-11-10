"""Session-05 test-only bounded pilot runner (Gates 6-8 preparation).

Drives the EXISTING production stage contracts (reasoning.py extraction packet
and validator, resolve_organisations/resolve_entities/resolve_goals,
tasks.build_ledger via the reasoning.review_task_packet seam, resolve_help)
over the Session-04 synthetic multilingual fixtures through the Session-04
PilotHarness. No production module is modified by this file. Nothing here
reads or transmits the original challenge dataset: only
`tests/pilot_fixtures/<packs>` contents, whose message bodies are synthetic,
enter any dispatch.

Approved representative allocation (user-approved Session 05 plan; the limits
are planning constraints, NOT spending authorization):

- EX-8 extraction dispatches: 2 window dispatches per language pack;
- ORG-2 organisation resolution: pilot_en, pilot_bn;
- ENT-3 entity resolution: pilot_en, pilot_hi, pilot_bn;
- GOALS-2 goal resolution: pilot_en, pilot_hi;
- TASK-7 task-interpretation observations: pilot_en x3 (M1, M2, M14),
  pilot_hi x1 (M4), pilot_bn x1 (M9), pilot_hn x2 (M5, M6);
- MATCH-2 matching-phase dispatches arise from the production matching
  contract on the sampled ledger events (pilot_en and pilot_hn in the
  offline plan);
- HELP-1 help resolution: pilot_en;

for exactly 25 planned base dispatches plus at most 5 recoveries inside the
30-transmission envelope. Stage dispatch counts depend on actual model output
in a real run; the envelope (transmission/recovery caps, 250k token
reservation, 600 s network deadline, USD 2.00 ceiling, fail-closed gates) is
enforced by PilotHarness either way while telemetry records the actuals.

OBSERVATION-DRIVEN DISPATCH (exact behaviour, not a gap): the counts above
are PLANNING ESTIMATES for task stages only. The per-pack task samples list
STABLE MESSAGE IDS, but the interpretation dispatches sent to the model are
the task_create/task_update observations the REAL extraction actually
produced for those samples; the runner never invents events to reach a
planned number. This is by design and was observed in the real retry run
(`session-08-gate-6-pilot-retry-evidence.json`): only one sampled pilot_hn
observation existed, so 6 of the 7 planned interpretations were dispatched;
both planned match jobs had no successfully interpreted events and help had
no open tasks, so nothing was dispatched for them and their prerequisite
stages stayed explicitly incomplete. Planned-vs-dispatched accounting is
therefore reconciled in evidence/telemetry, never fabricated upstream.

Known offline limitations, deliberately disclosed and never hidden:
- The deterministic mock's stage routing tables require observations that the
  scoped pilot deliberately does not extract (e.g. entity decisions cite
  C_PAIR/C_QUOTE scenes). Offline stages then record explicit failures after
  exactly one transmission each; bookkeeping accounting is unaffected. A real
  model can complete those stages contractually: seeded people need no
  evidence and direct chats are evidence-optional by rule.
- resolve_help validates its candidate against full people/chat coverage, so
  an offline entity failure makes the help stage record an explicit
  incomplete state instead of publishing output. No output is fabricated.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from data import load_input, build_windows
from llm import LLMError
from pilot_harness import PilotHarness, PilotRefusal
from reasoning import (EXTRACTION_PROMPT, EXTRACTION_VERSION, _encoded,
                       _identifier, review_task_packet, resolve_entities,
                       resolve_goals, resolve_help, resolve_organisations,
                       validate_extraction, window_packet)
from tasks import build_ledger
from validation import ValidationError

FIXTURE_ROOT = PROJECT / "tests" / "pilot_fixtures"
EVIDENCE_DIR = PROJECT / "ai-logs" / "opencode"

# Official published paid-tier price table (public documentation, not
# credentials). Used only for conservative projection: an approved free-tier
# pilot costs USD 0.00 but stays budgeted against this verified table.
# Re-verified independently in Session 08 (2026-11-08) against Google's
# official documentation; the harness normalizes the required * fields.
VERIFIED_PRICING = {
    "model": "gemini-3.5-flash-lite",
    "source": "https://ai.google.dev/gemini-api/docs/pricing "
              "(Gemini 3.5 Flash-Lite, Standard rates), retrieved 2026-11-08 "
              "(Session 08 re-verification); exact stable model code "
              "https://ai.google.dev/gemini-api/docs/models/"
              "gemini-3.5-flash-lite",
    "currency": "USD",
    "input_usd_per_mtok": 0.30,
    "output_usd_per_mtok": 2.50,
    "verification": {
        "re_verified": "2026-11-08 (Session 08, official Google documentation)",
        "model_id": "gemini-3.5-flash-lite (stable; no preview suffix)",
        "free_tier": "input and output Free of charge; no billing activated; "
                     "no paid fallback authorized",
        "structured_output": "Response format supported per the model page; "
                             "calls use response_format json_object only",
        "temperature": "Deprecated and ignored for this model; the client "
                       "omits the key for gemini-3-prefixed model IDs",
        "context_caching_paid_usd_per_mtok": 0.03,
        "free_tier_context_caching": "Not available (unused by this pilot)",
        "free_tier_quotas": "Per-model RPM/TPM/RPD now delegated to AI Studio "
                            "by the rate-limits page; the recorded planning "
                            "quotas (15 RPM / 250K TPM / 500 RPD) stay the "
                            "working assumption, and serialized dispatch plus "
                            "429/Retry-After backoff absorbs throttling "
                            "either way",
    },
}

PACK_ORDER = ("pilot_en", "pilot_hi", "pilot_bn", "pilot_hn")

# Per-pack pilot plan: chat windows to extract (the first window of each
# listed chat, built with production defaults), and downstream stages. The
# task sample lists STABLE message IDs; sampled observations are the ones
# whose every evidence span cites one of them.
ALLOCATION = {
    "pilot_en": {"windows": ("C_MAIN", "C_ORG"), "organisation": True,
                 "entities": "pilot-scope", "goals": True,
                 "task_sample": ("M1", "M2", "M14"), "help": True},
    "pilot_hi": {"windows": ("C_MAIN", "C_QUOTE"), "organisation": None,
                 "entities": "seed-only-scope", "goals": True,
                 "task_sample": ("M4",), "help": False},
    "pilot_bn": {"windows": ("C_MAIN", "C_ORG"), "organisation": True,
                 "entities": "pilot-scope", "goals": None,
                 "task_sample": ("M9",), "help": False},
    "pilot_hn": {"windows": ("C_MAIN", "C_QUOTE"), "organisation": None,
                 "entities": None, "goals": None,
                 "task_sample": ("M5", "M6"), "help": False},
}


def count_plan():
    """Planned base dispatches by stage. Offline-mock totals; real runs record
    actuals and stay inside the envelope either way."""
    per_pack = {}
    extraction = organisations = entities = goals = help_jobs = 0
    interp = match = 0
    for pack, spec in ALLOCATION.items():
        windows = len(spec["windows"])
        mobs = windows
        morg = int(bool(spec["organisation"]))
        ment = int(bool(spec["entities"]))
        mgoals = int(bool(spec["goals"]))
        minterp = len(spec["task_sample"])
        # With identical offline samples the production matching phase runs
        # only where a same-chat ledger candidate exists:
        mmatch = 1 if pack in ("pilot_en", "pilot_hn") else 0
        mhelp = int(bool(spec["help"]))
        per_pack[pack] = {"extraction": windows, "organisation": morg,
                          "entities": ment, "goals": mgoals,
                          "task_interpretation": minterp,
                          "task_matching": mmatch, "help": mhelp,
                          "total": windows + morg + ment + mgoals +
                          minterp + mmatch + mhelp,
                          "task_sample": list(spec["task_sample"]),
                          "chat_windows": list(spec["windows"])}
        extraction += windows
        organisations += morg
        entities += ment
        goals += mgoals
        interp += minterp
        match += mmatch
        help_jobs += mhelp
    return {"planned_base_calls": extraction + organisations + entities +
            goals + interp + match + help_jobs, "extraction": extraction,
            "organisations": organisations, "entities": entities,
            "goals": goals, "task_interpretation": interp,
            "task_matching": match, "help": help_jobs, "per_pack": per_pack}


def orgs_pilot_scope():
    """Pilot-scope organisation result for packs whose plan skips ORG.

    Truthful within scope: no organisation observation was extracted there,
    so no organisation record could exist. Marked and disclosed; only feeds
    the entity stage's state prerequisite within this runner.
    """
    return {"state": "succeeded_empty", "items": [], "aliases": {},
            "provenance": {}, "pending": [], "rejected": [], "failures": [],
            "pilot_scope": True}


class _HarnessClient:
    """Routes stage-function client.request(...) through the harness, with
    EXACTLY ONE telemetry job per dispatch (the instrumentation lives here and
    in the extraction window dispatcher; nothing else wraps a request).

    Stage functions call client.request([...], max_tokens=...) with the message
    list positional while the harness accepts keyword arguments only.
    Task reviewer packets carry their phase inside messages[1] ("interpret" or
    "match"); every other dispatch uses the stage label set before the call.
    Budget-related errors are re-raised for the stage function to record while
    harness.stop() is set so no further pack dispatches.
    """

    def __init__(self, harness, run, pack):
        self._harness = harness
        self._run = run
        self._pack = pack
        self.stage = "stage"

    def _label(self, messages):
        if (isinstance(messages, list) and len(messages) > 1 and
                isinstance(messages[1], dict)):
            try:
                packet = json.loads(messages[1]["content"])
            except (ValueError, TypeError, KeyError):
                packet = None
            if isinstance(packet, dict):
                phase = packet.get("phase")
                if phase in ("interpret", "match"):
                    return "task_" + phase
        return self.stage

    def request(self, messages=None, **kwargs):
        if messages is not None:
            kwargs["messages"] = messages
        label = self._label(messages)
        job = self._run._begin(self._pack, label, label)
        try:
            result = self._harness.request(**kwargs)
        except Exception as failure:
            self._run._end(job, kwargs.get("job_id"), failure)
            raise
        self._run._end(job, kwargs.get("job_id"))
        return result


class PilotRun:
    """One supervised execution; evidence never contains credentials or
    original conversation content (fixtures are synthetic)."""

    def __init__(self, harness):
        self.harness = harness
        self.jobs = []
        self.stage_states = {}
        self.extractions = {}
        self.fixture_hashes = {}

    def _begin(self, pack, stage, label):
        return {"pack": pack, "stage": stage, "label": label,
                "records_before": len(self.harness.budget.records)}

    def _end(self, job, job_id=None, error=None):
        records = self.harness.budget.records
        job["job_id"] = job_id
        slices = records[job["records_before"]:]
        if not slices:
            job["dispatched"] = False
            if error is not None:
                detail = getattr(error, "detail", None)
                job["error_code"] = (detail.get("code")
                                     if isinstance(detail, dict)
                                     else type(error).__name__)
        else:
            job["dispatched"] = True
            entries = []
            for record in slices:
                entries.append({
                    "attempt": record["attempt"], "recovery": record["recovery"],
                    "retry": record["retry"], "outcome": record["outcome"],
                    "http_status": record.get("http_status"),
                    "elapsed_s": round(record["elapsed"], 6),
                    "wait_s": round(record["wait"], 6),
                    "unknown_usage": record["unknown_usage"],
                    "reported_prompt_tokens": record["reported_prompt_tokens"],
                    "reported_completion_tokens": record["reported_completion_tokens"],
                    "reported_total_tokens": record["reported_total_tokens"],
                    "charged_tokens": record["charged_tokens"],
                    "additional_usage": dict(record["additional_usage"])})
                job["model"] = None
            job["transmissions"] = entries
            job["outcome"] = slices[-1]["outcome"]
            metadata = self.harness.client.last_metadata
            if metadata is not None:
                job["finish_reason"] = metadata.get("finish_reason")
                job["model"] = metadata.get("model")
        if error is not None and job["dispatched"]:
            detail = getattr(error, "detail", None)
            job["error_code"] = (detail.get("code") if isinstance(detail, dict)
                                 else type(error).__name__)
            # Local-only diagnostics: safe detail text and, for HTTP
            # failures, the status class the transport observed. Never any
            # provider body or private content.
            if isinstance(detail, dict):
                job["error_detail"] = detail.get("message")
                if detail.get("status") is not None:
                    job["http_status"] = detail["status"]
        if error is not None:
            detail = getattr(error, "detail", None)
            code = detail.get("code") if isinstance(detail, dict) else None
            if code in ("call_budget", "recovery_budget", "token_budget",
                        "attempt_limit"):
                self.harness.stop(code)
        self.jobs.append(job)

    # --------------------------------------------------------- extraction
    def _dispatch_window(self, pack, data, plan, index):
        job = self._begin(pack, "extraction", "EX")
        window = plan.windows[index]
        fingerprint = _identifier({
            "messages": [r.original for r in data.message_records],
            "chats": [r.original for r in data.chat_records],
            "seed": data.seed})
        job_id = "extract:" + fingerprint[:16] + ":" + str(index)
        packet = window_packet(data, window)
        def validate(text):
            validate_extraction(text, data, window)
        observations, error = [], None
        try:
            text = self.harness.request(
                messages=[{"role": "system", "content": EXTRACTION_PROMPT},
                          {"role": "user", "content": _encoded(packet).decode("utf-8")}],
                max_tokens=4096, response_format={"type": "json_object"},
                job_id=job_id, validate=validate,
                # Session-08 correction: the 2026-11-08 real run truncated all
                # four window-0 jobs at 2044/2048 completion tokens
                # (finish_reason "length"). 4096 matches the entities/goals
                # caps; organisations/task-review keep 2048. Production
                # extract_windows stays 2048 for the pilot scope.
                cache_context={"stage": "extraction",
                               "prompt_version": EXTRACTION_VERSION,
                               "schema_version": 1,
                               "input_fingerprint": fingerprint,
                               "timezone_policy": "UTC", "as_of": data.as_of})
            observations = validate_extraction(text, data, window)
        except PilotRefusal:
            self._end(job, job_id)
            raise
        except (LLMError, ValueError, OSError, KeyError) as failure:
            error = failure
            if isinstance(failure, ValueError):
                code = "invalid_response"
            elif isinstance(failure, LLMError):
                # Surface the real local classification (truncated, validation,
                # ...) instead of a generic request_failed in the evidence.
                code = failure.detail.get("code", "request_failed")
            else:
                code = "request_failed"
            self.extractions[pack]["failures"].append({"job": job_id, "code": code})
        self._end(job, job_id, error)
        return observations, job_id

    def _extraction_scope(self, pack, data, plan):
        """Mirror extract_windows per-window merging for the pilot scope."""
        result = {"state": "running", "required": [], "completed": [],
                  "failures": [], "observations": [], "pilot_scope": True,
                  "windows": []}
        self.extractions[pack] = result
        merged = {}
        for chat_id in ALLOCATION[pack]["windows"]:
            index = next(i for i, window in enumerate(plan.windows)
                         if window.chat_id == chat_id)
            try:
                observations, job_id = self._dispatch_window(pack, data, plan, index)
            except PilotRefusal:
                # Let the refusal propagate; run_pilot stops the harness with
                # its real code (transmission_cap, unknown_usage, ...) so the
                # evidence records the exact cause.
                raise
            result["required"].append(job_id)
            result["completed"].append(job_id)
            result["windows"].append(job_id)
            for observation in observations:
                observation["subjects"] = sorted(set(observation["subjects"]))
                observation["evidence"] = sorted(observation["evidence"],
                                                 key=_encoded)
                identifier = _identifier(observation)
                if identifier not in merged:
                    merged[identifier] = dict(observation, id=identifier,
                                              windows=[])
                if job_id not in merged[identifier]["windows"]:
                    merged[identifier]["windows"].append(job_id)
            result["observations"] = [merged[key] for key in sorted(merged)]
        result["state"] = ("incomplete" if result["failures"] else
                           "succeeded" if merged else "succeeded_empty")
        return result

    # ------------------------------------------------------------- stages
    def run_pack(self, pack, data, plan):
        spec = ALLOCATION[pack]
        client = _HarnessClient(self.harness, self, pack)
        extraction = self._extraction_scope(pack, data, plan)
        if self.harness.stopped is not None:
            return
        results = {}

        def record_stage(stage, value):
            results[stage] = value
            summary = {"state": value.get("state"),
                       "failures": len(value.get("failures", []))}
            pending = value.get("pending")
            if isinstance(pending, list):
                summary["pending"] = len(pending)
            unresolved = value.get("unresolved")
            if isinstance(unresolved, list):
                summary["unresolved"] = len(unresolved)
            self.stage_states[pack + "/" + stage] = summary

        if spec["organisation"]:
            client.stage = "organisations"
            record_stage("organisations",
                         resolve_organisations(data, extraction, client))
            if self.harness.stopped is not None:
                return
        organisations = (results.get("organisations", {}) if spec["organisation"]
                         else orgs_pilot_scope())
        if spec["entities"]:
            client.stage = "entities"
            record_stage("entities",
                         resolve_entities(data, extraction, organisations, client))
            if self.harness.stopped is not None:
                return
        if spec["goals"]:
            client.stage = "goals"
            record_stage("goals", resolve_goals(data, extraction, client))
            if self.harness.stopped is not None:
                return

        sample_ids = set(spec["task_sample"])
        ledger_scope = {
            "state": extraction["state"], "required": extraction["required"],
            "completed": extraction["completed"], "failures": [],
            "observations": [o for o in extraction["observations"]
                             if o["kind"] in ("task_create", "task_update") and
                             all(span["message_id"] in sample_ids
                                 for span in o["evidence"])],
        }
        # Phase labels come from inside _HarnessClient.request, which already
        # instruments every dispatch exactly once.
        ledger = build_ledger(data, ledger_scope,
                              lambda packet, validate:
                              review_task_packet(client, packet, validate))
        record_stage("tasks", ledger)
        if self.harness.stopped is not None:
            return

        if not spec["help"]:
            return
        output = {key: [] for key in
                  ("people", "organisations", "chats", "goals", "open_loops")}
        output.update(people=results.get("entities", {}).get("people", []),
                      organisations=organisations.get("items", []),
                      chats=results.get("entities", {}).get("chats", []),
                      goals=results.get("goals", {}).get("items", []))
        for task in ledger.get("tasks", []):
            item = {"title": task["action"] + " " + task["object"],
                    "type": task["type"], "owner": task["owner"],
                    "chat_id": task["chat_id"], "source_msg": task["source_msg"],
                    "status": task["status"], "due": task["due"]}
            if task["closed_by"] is not None:
                item["closed_by"] = task["closed_by"]
            output["open_loops"].append(item)
        client.stage = "help"
        try:
            record_stage("help", resolve_help(data, output, ledger, client))
        except ValidationError:
            # Disclosed offline limitation: the help candidate must pass the
            # full five-array coverage validation, which scoped extraction
            # cannot satisfy. Recorded explicitly; nothing is fabricated.
            record_stage("help", {"state": "incomplete",
                                  "failures": [{"stage": "help",
                                                "code": "invalid_candidate"}]})

    # ---------------------------------------------------------------- run
    def execute(self):
        packs = {}
        for pack in PACK_ORDER:
            fixture = FIXTURE_ROOT / pack
            data = load_input(fixture)
            data.require_complete()
            packs[pack] = data
            self.fixture_hashes[pack] = {
                name: hashlib.sha256((fixture / name).read_bytes()).hexdigest()
                for name in ("chats.jsonl", "messages.jsonl", "seed.json")}
        for pack in PACK_ORDER:
            data = packs[pack]
            plan = build_windows(data)
            plan.require_complete()
            self.run_pack(pack, data, plan)
            if self.harness.stopped is not None:
                break

    def evidence(self, mode, pricing=None):
        summary = self.harness.budget.summary()
        document = {
            "purpose": "Session-05 bounded pilot evidence (synthetic fixtures "
                       "only). The envelope is a planning constraint, not a "
                       "spend grant.",
            "mode": mode,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "envelope": {
                "max_transmissions": self.harness.limits.max_transmissions,
                "max_recoveries": self.harness.limits.max_recoveries,
                "token_reservation": self.harness.limits.token_reservation,
                "spend_ceiling_usd": self.harness.limits.spend_ceiling_usd,
                "network_seconds": self.harness.limits.network_seconds},
            "planned": count_plan()["planned_base_calls"],
            "telemetry": self.jobs,
            "stage_states": self.stage_states,
            "budget_summary": summary,
            "fixture_sha256": self.fixture_hashes,
            "synthetic_only": True,
            "stopped": self.harness.stopped,
        }
        if pricing is not None:
            document["verified_pricing"] = pricing
            document["projected_usd"] = self.harness.projected_usd()
        caps = (summary["attempts"] <= self.harness.limits.max_transmissions and
                summary["recoveries"] <= self.harness.limits.max_recoveries and
                not summary["over_ceiling"] and
                summary["elapsed"] <= self.harness.limits.network_seconds)
        document["envelope_verified"] = bool(caps)
        document["run_state"] = ("stopped: " + self.harness.stopped
                                 if self.harness.stopped is not None
                                 else "completed")
        return document


def run_pilot(mode="test", transport=None, clock=time.monotonic, sleep=time.sleep,
              verified_pricing=None, provider_controls_confirmed=False,
              evidence_path=None, capture_path=None, capture_max_bytes=4096):
    """Run the bounded pilot and return its evidence document.

    mode == "test" requires an injected offline transport (no network).
    mode == "real" additionally requires verified pricing, user-confirmed
    provider-side spend controls and runtime environment credentials before
    dispatch, and is gated upstream by explicit user authorization.
    capture_path (optional) writes a separate bounded response-capture file
    for Gate 6/7 diagnosis: successful and failed structured responses with
    stage/job identifiers, finish reasons, HTTP status and local validation
    outcomes. Bodies are byte-capped; request bodies, transport headers and
    credentials are never captured. The capture file is never overwritten.
    """
    if mode == "test" and transport is None:
        return {"run_state": "refused", "stopped": "configuration",
                "error_code": "configuration",
                "message": "Offline runs require an injected transport.",
                "synthetic_only": True}
    if capture_path is not None:
        if evidence_path is not None and Path(capture_path) == Path(evidence_path):
            return {"run_state": "refused", "stopped": "configuration",
                    "error_code": "configuration",
                    "message": "Evidence and response captures must be "
                               "distinct files.",
                    "synthetic_only": True}
        if Path(capture_path).exists():
            return {"run_state": "refused", "stopped": "capture_exists",
                    "error_code": "capture_exists",
                    "message": "Target capture file already exists and is "
                               "never overwritten: " + str(Path(capture_path)),
                    "synthetic_only": True}
    captured = []
    try:
        harness = PilotHarness(transport=transport, clock=clock, sleep=sleep,
                               verified_pricing=verified_pricing,
                               provider_controls_confirmed=provider_controls_confirmed,
                               capture=captured.append,
                               capture_max_bytes=capture_max_bytes)
    except PilotRefusal as refusal:
        return {"run_state": "refused", "stopped": refusal.code,
                "error_code": refusal.code, "message": refusal.args[0],
                "synthetic_only": True}
    run = PilotRun(harness)
    try:
        run.execute()
    except PilotRefusal as refusal:
        run.harness.stop(refusal.code)
    document = run.evidence(mode, pricing=verified_pricing)
    if capture_path is not None:
        document["response_captures"] = {
            "count": len(captured),
            "capture_failures": harness.client.capture_failures,
            "path": Path(capture_path).name}
        capture_document = {
            "purpose": "Session-08 bounded response capture for Gate 6/7 "
                       "diagnosis: successful and failed structured model "
                       "responses with local stage/job identifiers, finish "
                       "reasons, HTTP status and validation outcomes. "
                       "Request bodies, transport headers and credentials "
                       "are never captured; dispatches carry the four "
                       "synthetic fixture packs only; bodies are byte-"
                       "capped with exact byte length and SHA-256 of the "
                       "uncapped response.",
            "mode": mode,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "capture_max_bytes": capture_max_bytes,
            "capture_count": len(captured),
            "capture_failures": harness.client.capture_failures,
            "synthetic_only": True,
            "stopped": harness.stopped,
            "captures": captured}
        path = Path(capture_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(capture_document, ensure_ascii=False,
                                    indent=2, sort_keys=True,
                                    allow_nan=False) + "\n")
    if evidence_path is not None:
        path = Path(evidence_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(document, ensure_ascii=False, indent=2,
                                    sort_keys=True, allow_nan=False) + "\n")
    return document


def describe_plan():
    """The approved representative allocation, for review and evidence."""
    return {"pack_order": list(PACK_ORDER), "allocation": ALLOCATION,
            "totals": count_plan()}
