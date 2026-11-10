"""Session-04 offline mock LLM for the synthetic pilot fixtures.

Test-only. Deterministic. No network, no credentials, no real model.

`respond(endpoint, wire, key, timeout)` is an injected `llm.Client` transport
that routes each production stage contract to a fixed reviewer decision table.
Decisions are keyed by STABLE MESSAGE IDS (M1..M18), never by observed text:
fixture bodies change per language pack; expectations do not.

Scene/target tables below are reviewer-side metadata. They never enter any
inference prompt: the mock only emits contract-valid stage responses.
"""
import json

SURFACE_NAMES = ("HomeServe", "\u0939\u094b\u092e\u0938\u0930\u094d\u0935", "\u09b9\u09cb\u09ae\u09b8\u09be\u09b0\u09cd\u09ad")
YEARS = {"M3": "2026-09-23", "M15": "2026-09-24"}


# ---------------------------------------------------------------- scenes
# message_id -> list of (kind, subjects, meaning) extraction observations.
# Evidence spans are materialized from the window packet at response time,
# so observation evidence always cites exactly the supplied primary span.
SCENES = {
    "M1": [
        ("task_create", ["P01"], "P01 commits to sending the signed lease copy; task origin"),
        ("chat", ["C_MAIN"], "Family coordination chat carries household commitments"),
    ],
    "M2": [
        ("person", ["P01"], "P01 is the user's spouse and confirms household errands"),
        ("task_update", ["P01"], "Acknowledgement of the lease-copy task; no closure evidence"),
    ],
    "M3": [
        ("task_create", ["P02"], "Tuition trial appointment should be confirmed for 23 September"),
        ("person", ["P02"], "P02 is household staff handling tuition logistics"),
    ],
    "M4": [
        ("task_update", ["P02"], "Negated cancellation: the tuition appointment remains booked"),
    ],
    "M5": [
        ("task_create", ["P02"], "P02 offers to coordinate the school pickup rota from Monday"),
    ],
    "M6": [
        ("task_update", ["P01"], "Owner reassignment: P01 coordinates the pickup rota instead"),
    ],
    "M7": [
        ("task_create", ["P03"], "Tuition reimbursement form submission"),
    ],
    "M8": [
        ("task_update", ["P03"], "Claimed completion of the reimbursement form"),
    ],
    "M9": [
        ("task_update", ["P03"], "Reopen: the reimbursement form is not done; approval pending"),
    ],
    "M10": [
        ("goal", ["ME"], "User states an explicit January half-marathon intention"),
    ],
    "M11": [
        ("goal", [], "Training start evidences pursuit of the marathon goal"),
    ],
    "M12": [
        ("goal", [], "Forwarded cousin's marathon plan; not the user's own intention"),
    ],
    "M13": [
        ("task_create", ["P01"], "Anniversary dinner caterer suggestions for next Saturday"),
    ],
    "M14": [
        ("task_update", [], "Sent the tuition invoice copy when convenient; scope ties to no task"),
    ],
    "M15": [
        ("task_create", ["ME"], "Book the dentist appointment for Thursday 24 September"),
        ("chat", ["C_PAIR"], "Errand chat tracks appointments for P06"),
        ("person", ["P06"], "P06 is a friend who requests bookings on their behalf"),
    ],
    "M16": [
        ("task_update", ["P05"], "Completion of the dentist booking quoted from another chat"),
        ("chat", ["C_QUOTE"], "Follow-up chat quotes the errand chat to report completion"),
        ("person", ["P05"], "P05 is a client who receives forwarded confirmations"),
    ],
    "M17": [
        ("organisation", ["C_ORG"], "Home services company coordinates appliance service updates"),
        ("chat", ["C_ORG"], "Vendor chat carries service-company notices"),
        ("person", ["P04"], "P04 is a vendor coordinating home services"),
    ],
    "M18": [],
}

PEOPLE_RECORDS = {"P01": "spouse", "P02": "staff", "P03": "colleague",
                  "P04": "vendor", "P05": "client", "P06": "friend"}
CHAT_PERSON = {"C_MAIN": "P01", "C_PAIR": "P06", "C_QUOTE": "P05"}
ORG_RECORD = {"name": None, "type": "company", "side": "home", "role": "helper"}
PERSON_OBS_BY_CHAT = {"P01": "M2", "P02": "M3", "P04": "M17",
                      "P05": "M16", "P06": "M15"}
CHAT_OBS = {"C_MAIN": "M1", "C_PAIR": "M15", "C_QUOTE": "M16", "C_ORG": "M17"}


# ------------------------------------------------------- task decisions
# observation evidence message set -> accepted semantics (operation).
INTERPRET = {
    frozenset({"M1"}): {"operation": "create", "source_msg": "M1", "evidence": ["M1"],
                        "details": {"action": "send", "object": "signed lease copy",
                                    "type": "commitment", "owner": "P01", "due": None}},
    frozenset({"M2"}): {"operation": "acknowledge", "source_msg": "M2",
                        "evidence": ["M2"], "details": {}},
    frozenset({"M3"}): {"operation": "create", "source_msg": "M3", "evidence": ["M3"],
                        "details": {"action": "confirm", "object": "tuition trial appointment",
                                    "type": "followup", "owner": "P02", "due": YEARS["M3"]}},
    frozenset({"M4"}): {"operation": "acknowledge", "source_msg": "M4",
                        "evidence": ["M4"], "details": {}},
    frozenset({"M5"}): {"operation": "create", "source_msg": "M5", "evidence": ["M5"],
                        "details": {"action": "coordinate", "object": "school pickup rota",
                                    "type": "commitment", "owner": "P02", "due": None}},
    frozenset({"M6"}): {"operation": "update", "source_msg": "M6", "evidence": ["M6"],
                        "details": {"owner": "P01"}},
    frozenset({"M7"}): {"operation": "create", "source_msg": "M7", "evidence": ["M7"],
                        "details": {"action": "submit", "object": "tuition reimbursement form",
                                    "type": "commitment", "owner": "P03", "due": None}},
    frozenset({"M8"}): {"operation": "complete", "source_msg": "M8",
                        "evidence": ["M8"], "details": {}},
    frozenset({"M9"}): {"operation": "reopen", "source_msg": "M9",
                        "evidence": ["M9"], "details": {}},
    frozenset({"M13"}): {"operation": "create", "source_msg": "M13", "evidence": ["M13"],
                         "details": {"action": "suggest", "object": "anniversary caterers",
                                     "type": "followup", "owner": "P01", "due": None}},
    frozenset({"M14"}): {"operation": "ambiguous", "source_msg": "M14",
                         "evidence": ["M14"], "details": {}},
    frozenset({"M15"}): {"operation": "create", "source_msg": "M15", "evidence": ["M15"],
                         "details": {"action": "book", "object": "dentist appointment",
                                     "type": "followup", "owner": "ME", "due": YEARS["M15"]}},
    frozenset({"M16"}): {"operation": "complete", "source_msg": "M16",
                         "evidence": ["M16"], "details": {}},
}

# event source_msg -> origin source_msg of the matched task.
MATCH_TARGET = {"M2": "M1", "M4": "M3", "M6": "M5",
                "M8": "M7", "M9": "M7", "M16": "M15"}

# matched task source_msg -> help decision.
HELP_BY_SOURCE = {
    "M1": {"help": {"action": "remind", "remind_at": "2026-09-26T09:00:00+05:30"},
           "evidence": ["M1", "M2"]},
    "M3": {"help": {"action": "leave",
                    "reason": "School confirmation is pending; stay out until it lands."},
           "evidence": ["M3", "M4"]},
    "M5": {"help": {"action": "assist",
                    "next_step": "Confirm Monday pickup cover with P01; needs your yes.",
                    "needs_yes": True},
           "evidence": ["M5", "M6"]},
    "M7": {"help": {"action": "leave",
                    "reason": "Approval is pending; do not remind until approved."},
           "evidence": ["M7", "M9"]},
    "M13": {"help": {"action": "leave",
                     "reason": "Personal family decision; low value to assist."},
            "evidence": ["M13"]},
}

GOAL_RECORD = {"title": "Run a half marathon in January", "area": "health",
               "type": "milestone", "horizon": "3mo"}
GOAL_SUPPORT_ROLES = {"M10": ("explicit", "e1"), "M11": ("pursuit", "e1")}


def _obs_index(packet):
    """(kind, message_id) -> observation id for decisions that must cite evidence."""
    index = {}
    for observation in packet.get("observations", []):
        for span in observation["evidence"]:
            index.setdefault((observation["kind"], span["message_id"]), observation["id"])
    return index


def _surface_name(text):
    for name in SURFACE_NAMES:
        if name in text:
            return name
    return SURFACE_NAMES[0]


# ------------------------------------------------------------ stages
def extraction_response(packet):
    """Exact primary coverage plus the scene observations for reviewed spans."""
    covered = []
    observations = []
    for span in packet["primary"]:
        covered.append({key: span[key] for key in ("message_id", "start", "end")})
        mid = span["message_id"]
        for kind, subjects, meaning in SCENES.get(mid, ()):
            observations.append({
                "kind": kind, "subjects": sorted(set(subjects)), "meaning": meaning,
                "evidence": [{"message_id": mid, "start": span["start"],
                              "end": span["end"], "text": span["text"]}],
            })
    return {"covered": covered, "observations": observations}


def organisation_response(packet):
    identifier = _obs_index(packet)
    oid = next(i for (kind, mid), i in sorted(identifier.items())
               if kind == "organisation")
    record = dict(ORG_RECORD)
    record["name"] = _surface_name(" ".join(
        span["text"] for observation in packet["observations"]
        if observation["id"] == oid for span in observation["evidence"]))
    return {"groups": [{"members": [oid], "record": record,
                        "aliases": [{"name": record["name"], "evidence": [oid]}]}],
            "rejected": [], "pending": []}


def entity_response(packet):
    identifier = _obs_index(packet)
    orgs = packet.get("organisations", [])
    org_id = orgs[0]["id"] if orgs else None
    decisions = []
    for category, target in packet["required"]:
        if category == "people":
            record = {"id": target, "circle": PEOPLE_RECORDS[target]}
            evidence = []
            message = PERSON_OBS_BY_CHAT.get(target)
            if message:
                evidence.append(identifier[("person", message)])
            if target == "P02":
                record["links"] = [{"organisation": org_id, "link": "supports"}]
                record["looks_after"] = ["P01"]
            decisions.append({"category": "people", "id": target,
                              "record": record, "evidence": evidence})
        else:
            if target == "C_ORG":
                record = {"chat_id": target, "organisation": org_id}
                evidence = [identifier[("chat", "M17")], identifier[("organisation", "M17")]]
            else:
                record = {"chat_id": target, "person": CHAT_PERSON[target]}
                evidence = [identifier[("chat", CHAT_OBS[target])]]
            decisions.append({"category": "chats", "id": target,
                              "record": record, "evidence": evidence})
    return {"decisions": decisions}
def goal_response(packet):
    identifier = _obs_index(packet)
    members, support, rejected = [], [], []
    for observation in packet["observations"]:
        mid = observation["evidence"][0]["message_id"]
        if mid == "M12":
            rejected.append({"id": observation["id"], "reason": "other_person"})
            continue
        members.append(observation["id"])
        role, episode = ("explicit", "e1") if mid == "M10" else ("pursuit", "e1")
        span = dict(observation["evidence"][0])
        support.append({"span": span, "role": role, "episode": episode, "antecedent": None})
    return {"groups": [{"members": members, "record": dict(GOAL_RECORD),
                        "support": support}],
            "rejected": rejected, "pending": []}


def _interpret_response(packet):
    ids = frozenset(span["message_id"] for span in packet["observation"]["evidence"])
    event = INTERPRET[ids]
    return dict(event, evidence=sorted(set(event["evidence"]) & ids) or event["evidence"])


def _match_response(packet):
    source = packet["event"]["source_msg"]
    origin = MATCH_TARGET.get(source)
    if origin is None:
        # Create events with nonempty candidate lists: no match, create instead.
        return {"decision": "none", "target": None, "evidence": [source]}
    target = next((task["id"] for task in packet["candidates"]
                   if task["source_msg"] == origin), None)
    if target is None:
        # The expected origin task is not among the candidates; flag it
        # explicitly instead of fabricating a match or going silent.
        return {"decision": "ambiguous", "target": None, "evidence": [source]}
    return {"decision": "match", "target": target,
            "evidence": sorted({source, origin})}


def _help_response(packet):
    decisions = []
    for task in packet["tasks"]:
        decision = HELP_BY_SOURCE[task["source_msg"]]
        decisions.append({"id": task["id"], **decision})
    return {"decisions": decisions}


def respond(endpoint, wire, key, timeout):
    """Injected `llm.Client` transport: (status, headers, body bytes)."""
    body = json.loads(wire)
    system = body["messages"][0]["content"]
    packet = json.loads(body["messages"][1]["content"])
    if "Extract observations" in system:
        payload = extraction_response(packet)
    elif packet.get("phase") == "interpret":
        payload = _interpret_response(packet)
    elif packet.get("phase") == "match":
        payload = _match_response(packet)
    elif "decisions:[{category" in packet.get("contract", ""):
        payload = entity_response(packet)
    elif "support:[{span" in packet.get("contract", ""):
        payload = goal_response(packet)
    elif "aliases:[{" in packet.get("contract", ""):
        payload = organisation_response(packet)
    else:
        payload = _help_response(packet)
    content = json.dumps(payload, ensure_ascii=False)
    prompt_tokens = len(wire) + 32
    completion_tokens = len(content) + 16
    usage = {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
             "total_tokens": prompt_tokens + completion_tokens}
    data = {"choices": [{"finish_reason": "stop", "message": {"content": content}}],
            "model": "mock-pilot-1", "usage": usage}
    return 200, {}, json.dumps(data, ensure_ascii=False).encode("utf-8")
